from app.contracts.notification_clients import WebPushClientContract
from app.contracts.repositories.notification_repositories import (
    NotificationPreferencesRepoContract,
    PushSubscriptionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.notifications.notification_settings import (
    MyNotificationSettingsView,
    NotificationSettingsQuery,
)
from app.use_cases.notifications.notification_views import settings_view


class GetNotificationSettingsUseCase(
    UseCaseContract[NotificationSettingsQuery, MyNotificationSettingsView]
):
    """
    The signed-in member's own notifications in a business: events and
    quiet hours, their devices, and the key browsers subscribe with (None
    while device notifications are off on this server).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        notification_preferences_repo: NotificationPreferencesRepoContract,
        push_subscription_repo: PushSubscriptionRepoContract,
        web_push_client: WebPushClientContract | None,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._notification_preferences_repo: NotificationPreferencesRepoContract = (
            notification_preferences_repo
        )
        self._push_subscription_repo: PushSubscriptionRepoContract = (
            push_subscription_repo
        )
        self._web_push_client: WebPushClientContract | None = web_push_client

    def run(self, input_data: NotificationSettingsQuery) -> MyNotificationSettingsView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        return settings_view(
            business,
            self._notification_preferences_repo.get(business.id, input_data.user_id),
            self._push_subscription_repo.list_by_user(business.id, input_data.user_id),
            None if self._web_push_client is None else self._web_push_client.public_key,
        )
