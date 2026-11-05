from typed_time_provider import Microseconds, WallClock

from app.contracts.notification_utilities import StaffLinkSignerContract
from app.contracts.notifications import StaffDeliveryRecorderContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.delivery_repositories import (
    OutboundMessageRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.deliveries import OutboundMessageKind, OutboundMessageStatus
from app.schemas.constants.notifications import StaffTextStyle
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.notifications.notification_settings import (
    ContactCheckCommand,
    NotificationCheckQueued,
)
from app.schemas.dto.notifications.staff_alerts import (
    StaffAlertBrief,
    StaffAlertBriefInput,
    StaffNotificationTextInput,
)
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.deliveries.strings import DeliveryErrorText
from app.use_cases.notifications.notification_checks import (
    check_brief,
    check_test_budget,
    settings_link,
)
from app.use_cases.notifications.notification_views import find_contact
from app.utilities.deliveries.delivery_keys import (
    derive_outbound_message_id,
    staff_idempotency_key,
    staff_recipient_key,
)
from app.utilities.notifications.staff_providers import (
    is_delivery_simulated,
    missing_staff_provider,
    staff_template,
)


class QueueContactCheckUseCase(
    UseCaseContract[ContactCheckCommand, NotificationCheckQueued]
):
    """
    The owner checks a staff contact: a short test notification ("this is
    where handoffs, requests and bookings will arrive", with a link to the
    notification settings) in the contact's language, stored in the outbox
    for sending right away. At most 5 tests per contact and hour. A channel
    without a provider stores it as failed with the reason.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        outbound_message_repo: OutboundMessageRepoContract,
        delivery_recorder: StaffDeliveryRecorderContract,
        rate_limits: RequestRateLimitRegistryContract,
        brief_transformer: TransformerContract[StaffAlertBriefInput, StaffAlertBrief],
        text_transformer: TransformerContract[StaffNotificationTextInput, MessageText],
        link_signer: StaffLinkSignerContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._outbound_message_repo: OutboundMessageRepoContract = outbound_message_repo
        self._delivery_recorder: StaffDeliveryRecorderContract = delivery_recorder
        self._rate_limits: RequestRateLimitRegistryContract = rate_limits
        self._brief_transformer: TransformerContract[
            StaffAlertBriefInput, StaffAlertBrief
        ] = brief_transformer
        self._text_transformer: TransformerContract[
            StaffNotificationTextInput, MessageText
        ] = text_transformer
        self._link_signer: StaffLinkSignerContract = link_signer
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ContactCheckCommand) -> NotificationCheckQueued:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        contact: ManagerContact = find_contact(business, input_data.contact_key)
        now: Microseconds = self._wall_clock.now_unix()
        recipient_key = staff_recipient_key(contact)
        check_test_budget(self._rate_limits, business, recipient_key, now)
        text: MessageText = self._text_transformer.transform(
            StaffNotificationTextInput(
                style=StaffTextStyle.BRIEF,
                language=contact.language,
                brief=check_brief(self._brief_transformer, business, contact.language),
                link=settings_link(
                    self._link_signer, self._app_settings, business, now
                ),
            )
        )
        refusal: DeliveryErrorText | None = missing_staff_provider(
            self._app_settings, contact.channel
        )
        idempotency_key = staff_idempotency_key(contact, None)
        message = OutboundMessageDocument(
            id=derive_outbound_message_id(business.id, idempotency_key),
            business_id=business.id,
            kind=OutboundMessageKind.STAFF_NOTIFICATION,
            idempotency_key=idempotency_key,
            recipient_key=recipient_key,
            staff_contact=contact,
            text=text,
            template=staff_template(self._app_settings, contact),
            status=(
                OutboundMessageStatus.PENDING
                if refusal is None
                else OutboundMessageStatus.DEAD
            ),
            last_error=refusal,
            created_at=now,
            updated_at=now,
        )
        self._outbound_message_repo.insert_if_new(message)
        self._delivery_recorder.record(message)
        return NotificationCheckQueued(
            message=message,
            is_simulated=is_delivery_simulated(self._app_settings, contact.channel),
        )
