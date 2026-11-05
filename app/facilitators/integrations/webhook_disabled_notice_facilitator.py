import logging

from app.contracts.integrations import WebhookDisabledNoticeFacilitatorContract
from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.notifications import StaffAlertFacilitatorContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.webhooks import WebhookDeliveryDocument, WebhookEndpointDocument
from app.schemas.dto.notifications.staff_alerts import StaffAlert
from app.schemas.typings.compliance.strings import AuditEntityReference
from app.schemas.typings.notifications.constrained_strings import (
    PushNotificationTag,
    StaffAlertSubject,
)
from app.utilities.integrations.webhook_disabled_texts import WebhookDisabledTexts
from app.utilities.integrations.webhook_endpoints import (
    WEBHOOK_ENDPOINT_ENTITY,
    endpoint_name,
)

logger: logging.Logger = logging.getLogger(__name__)


class WebhookDisabledNoticeFacilitator(WebhookDisabledNoticeFacilitatorContract):
    """
    Tells a business that one of its webhook endpoints was switched off on
    its own (WEBHOOK_DISABLED_AFTER_FAILURES failures in a row, or 410
    Gone):

    - one staff alert, news for every staff contact of the business
      (e-mail, Telegram, WhatsApp, SMS) whatever events they chose, and for
      the owners' devices (only owners can switch it on again), held
      through quiet hours, with a link to Settings → Integrations. Its
      subject is the delivery whose attempt switched the endpoint off: a
      retried delivery job never repeats it, an endpoint switched on and
      off again (by another delivery) is announced again;
    - an audit entry without an actor (the platform switched it off);
    - a live event, so an open Integrations card shows it switched off.

    Never raises: the switch-off itself is stored already.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        staff_alerts: StaffAlertFacilitatorContract,
        audit_log_repo: AuditLogRepoContract,
        live_events: EventPublisherFacilitatorContract,
        localized_text_resolver: LocalizedTextResolverContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._staff_alerts: StaffAlertFacilitatorContract = staff_alerts
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._resolver: LocalizedTextResolverContract = localized_text_resolver

    def notice_disabled(
        self,
        endpoint: WebhookEndpointDocument,
        delivery: WebhookDeliveryDocument,
    ) -> None:
        try:
            self._notice(endpoint, delivery)
        except Exception:
            logger.exception(
                "The notice of switched-off webhook %s failed.", endpoint.id
            )

    def _notice(
        self,
        endpoint: WebhookEndpointDocument,
        delivery: WebhookDeliveryDocument,
    ) -> None:
        switched_off_at = endpoint.disabled_at or endpoint.updated_at
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=endpoint.business_id,
                action=AuditAction.UPDATE,
                entity=WEBHOOK_ENDPOINT_ENTITY,
                entity_id=AuditEntityReference(str(endpoint.id)),
                created_at=switched_off_at,
                updated_at=switched_off_at,
            )
        )
        self._live_events.publish(
            endpoint.business_id, LiveEventKind.WEBHOOK_CHANGED, (endpoint.id,)
        )
        business: BusinessDocument | None = self._business_repo.get(
            endpoint.business_id
        )
        if business is None:
            return

        self._staff_alerts.alert(
            business,
            StaffAlert(
                business_id=business.id,
                target=StaffLinkTarget.INTEGRATIONS,
                tag=PushNotificationTag(f"webhook_disabled:{endpoint.id}"),
                subject=StaffAlertSubject(f"webhook_disabled:{delivery.id}"),
                member_roles=[BusinessMemberRole.OWNER],
            ),
            WebhookDisabledTexts(
                self._resolver,
                business.name,
                endpoint_name(endpoint),
                endpoint.consecutive_failures,
                delivery.last_problem,
            ),
        )
