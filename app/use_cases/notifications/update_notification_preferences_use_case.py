from typed_time_provider import Microseconds, WallClock

from app.contracts.notification_clients import WebPushClientContract
from app.contracts.repositories.notification_repositories import (
    NotificationPreferencesRepoContract,
    PushSubscriptionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.notifications import StaffAlertEvent
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.notification_preferences import (
    StaffNotificationPreferences,
    UserNotificationPreferencesDocument,
)
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.notifications.notification_settings import (
    MyNotificationSettingsView,
    UpdateNotificationPreferencesCommand,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.use_cases.notifications.notification_views import settings_view
from app.utilities.notifications.quiet_hours import is_valid_quiet_hours
from app.utilities.notifications.staff_delivery_keys import preferences_id_of


class UpdateNotificationPreferencesUseCase(
    UseCaseContract[UpdateNotificationPreferencesCommand, MyNotificationSettingsView]
):
    """
    A member chooses which events reach their devices and their quiet hours
    (business time zone; urgent handoffs still come through). Quiet hours
    must have a length.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        notification_preferences_repo: NotificationPreferencesRepoContract,
        push_subscription_repo: PushSubscriptionRepoContract,
        web_push_client: WebPushClientContract | None,
        wall_clock: WallClock[Microseconds],
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
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(
        self,
        input_data: UpdateNotificationPreferencesCommand,
    ) -> MyNotificationSettingsView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        quiet_hours = input_data.request.quiet_hours
        if quiet_hours is not None and not is_valid_quiet_hours(quiet_hours):
            raise ValidationFailedError(
                "Quiet hours must start and end at different times."
            )

        now: Microseconds = self._wall_clock.now_unix()
        stored = self._notification_preferences_repo.get(
            business.id, input_data.user_id
        )
        preferences = UserNotificationPreferencesDocument(
            id=preferences_id_of(business.id, input_data.user_id),
            business_id=business.id,
            user_id=input_data.user_id,
            preferences=StaffNotificationPreferences(
                events=[
                    event
                    for event in StaffAlertEvent
                    if event in input_data.request.events
                ],
                quiet_hours=quiet_hours,
            ),
            created_at=now if stored is None else stored.created_at,
            updated_at=now,
        )
        self._notification_preferences_repo.save(preferences)
        return settings_view(
            business,
            preferences,
            self._push_subscription_repo.list_by_user(business.id, input_data.user_id),
            None if self._web_push_client is None else self._web_push_client.public_key,
        )
