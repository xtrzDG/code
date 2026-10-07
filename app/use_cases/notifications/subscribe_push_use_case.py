from typed_time_provider import Microseconds, WallClock

from app.contracts.notification_clients import WebPushClientContract
from app.contracts.repositories.notification_repositories import (
    PushSubscriptionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.push_subscriptions import PushSubscriptionDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.notifications.notification_settings import (
    PushDeviceView,
    SubscribePushCommand,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.use_cases.notifications.notification_views import device_view
from app.utilities.notifications.push_endpoints import (
    are_valid_push_keys,
    is_supported_push_endpoint,
)
from app.utilities.notifications.staff_delivery_keys import push_subscription_id

# Devices of one user in one business; subscribing another one replaces
# the one turned on longest ago.
MAX_DEVICES_PER_USER: int = 10


class SubscribePushUseCase(UseCaseContract[SubscribePushCommand, PushDeviceView]):
    """
    "Enable notifications on this device": a member's browser subscription
    for the business's notifications, in the cabinet's language. The same
    browser subscribing again keeps one device (its keys and language are
    updated). Only the known push services are accepted (the server posts
    to the address given), and only real keys.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        push_subscription_repo: PushSubscriptionRepoContract,
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
        self._web_push_client: WebPushClientContract | None = web_push_client
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: SubscribePushCommand) -> PushDeviceView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        if self._web_push_client is None:
            raise ConflictError(
                "Notifications on devices are not set up on this server."
            )

        request = input_data.request
        if not is_supported_push_endpoint(
            str(request.endpoint), self._app_settings.environment
        ):
            raise ValidationFailedError("This browser's push service is not supported.")

        if not are_valid_push_keys(str(request.keys.p256dh), str(request.keys.auth)):
            raise ValidationFailedError("The push subscription keys are not valid.")

        now: Microseconds = self._wall_clock.now_unix()
        subscription_id = push_subscription_id(
            business.id, input_data.user_id, str(request.endpoint)
        )
        devices: list[PushSubscriptionDocument] = (
            self._push_subscription_repo.list_by_user(business.id, input_data.user_id)
        )
        stored: PushSubscriptionDocument | None = next(
            (device for device in devices if device.id == subscription_id), None
        )
        subscription = PushSubscriptionDocument(
            id=subscription_id,
            business_id=business.id,
            user_id=input_data.user_id,
            endpoint=request.endpoint,
            keys=request.keys,
            language=request.language,
            delivered_at=None if stored is None else stored.delivered_at,
            created_at=now if stored is None else stored.created_at,
            updated_at=now,
        )
        self._push_subscription_repo.save(subscription)
        if stored is None:
            self._forget_oldest(business, devices)

        return device_view(subscription)

    def _forget_oldest(
        self,
        business: BusinessDocument,
        devices: list[PushSubscriptionDocument],
    ) -> None:
        excess: int = len(devices) + 1 - MAX_DEVICES_PER_USER
        for device in sorted(devices, key=lambda item: int(item.created_at))[
            : max(excess, 0)
        ]:
            self._push_subscription_repo.delete(business.id, device.id)
