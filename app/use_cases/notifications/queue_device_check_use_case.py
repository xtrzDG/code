from typed_time_provider import Microseconds, WallClock

from app.contracts.notification_clients import WebPushClientContract
from app.contracts.notification_utilities import StaffLinkSignerContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.delivery_repositories import (
    OutboundMessageRepoContract,
)
from app.contracts.repositories.notification_repositories import (
    PushSubscriptionRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.deliveries import OutboundMessageKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument, PushRecipient
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.notifications.notification_settings import (
    NotificationCheckQueued,
    PushDeviceCommand,
)
from app.schemas.dto.notifications.staff_alerts import (
    StaffAlertBrief,
    StaffAlertBriefInput,
)
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.notifications.constrained_strings import PushNotificationTag
from app.use_cases.notifications.notification_checks import (
    check_brief,
    check_test_budget,
    settings_link,
)
from app.use_cases.notifications.notification_views import require_own_device
from app.utilities.deliveries.delivery_keys import derive_outbound_message_id
from app.utilities.notifications.staff_delivery_keys import (
    push_idempotency_key,
    push_recipient_key,
)

CHECK_TAG: PushNotificationTag = PushNotificationTag("check:notifications")


class QueueDeviceCheckUseCase(
    UseCaseContract[PushDeviceCommand, NotificationCheckQueued]
):
    """
    A member checks one of their devices: a test notification in the
    device's language that opens the notification settings, stored in the
    outbox for sending right away. At most 5 per device and hour.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        push_subscription_repo: PushSubscriptionRepoContract,
        outbound_message_repo: OutboundMessageRepoContract,
        rate_limits: RequestRateLimitRegistryContract,
        brief_transformer: TransformerContract[StaffAlertBriefInput, StaffAlertBrief],
        link_signer: StaffLinkSignerContract,
        web_push_client: WebPushClientContract | None,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._push_subscription_repo: PushSubscriptionRepoContract = (
            push_subscription_repo
        )
        self._outbound_message_repo: OutboundMessageRepoContract = outbound_message_repo
        self._rate_limits: RequestRateLimitRegistryContract = rate_limits
        self._brief_transformer: TransformerContract[
            StaffAlertBriefInput, StaffAlertBrief
        ] = brief_transformer
        self._link_signer: StaffLinkSignerContract = link_signer
        self._web_push_client: WebPushClientContract | None = web_push_client
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PushDeviceCommand) -> NotificationCheckQueued:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        device = require_own_device(self._push_subscription_repo, business, input_data)
        if self._web_push_client is None:
            raise ConflictError(
                "Notifications on devices are not set up on this server."
            )

        now: Microseconds = self._wall_clock.now_unix()
        recipient_key = push_recipient_key(device.id)
        check_test_budget(self._rate_limits, business, recipient_key, now)
        brief = check_brief(self._brief_transformer, business, device.language)
        idempotency_key = push_idempotency_key(device.id, None)
        message = OutboundMessageDocument(
            id=derive_outbound_message_id(business.id, idempotency_key),
            business_id=business.id,
            kind=OutboundMessageKind.STAFF_NOTIFICATION,
            idempotency_key=idempotency_key,
            recipient_key=recipient_key,
            push=PushRecipient(
                subscription_id=device.id,
                user_id=device.user_id,
                title=brief.title,
                url=settings_link(self._link_signer, self._app_settings, business, now),
                tag=CHECK_TAG,
            ),
            text=MessageText("" if brief.detail is None else str(brief.detail)),
            created_at=now,
            updated_at=now,
        )
        self._outbound_message_repo.insert_if_new(message)
        return NotificationCheckQueued(message=message)
