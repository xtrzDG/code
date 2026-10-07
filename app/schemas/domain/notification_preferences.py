from base_pydantic_schemas import BaseDocument, PersistentDocument
from pydantic import Field

from app.schemas.constants.notifications import StaffAlertEvent
from app.schemas.typings.bookings.constrained_strings import LocalTimeOfDay
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.notifications.prefixed_id import NotificationPreferencesId
from app.schemas.typings.users.prefixed_id import UserId

ALL_STAFF_ALERT_EVENTS: tuple[StaffAlertEvent, ...] = tuple(StaffAlertEvent)


def all_staff_alert_events() -> list[StaffAlertEvent]:
    return list(ALL_STAFF_ALERT_EVENTS)


class QuietHours(PersistentDocument):
    """
    A daily stretch in the business time zone when notifications wait
    (`starts_at` to `ends_at`, across midnight when it ends earlier than it
    starts). Urgent handoffs still come through.
    """

    starts_at: LocalTimeOfDay
    ends_at: LocalTimeOfDay


class StaffNotificationPreferences(PersistentDocument):
    """
    What reaches one recipient (a staff contact, or a cabinet user's
    devices): which events, and quiet hours when they wait.
    """

    events: list[StaffAlertEvent] = Field(default_factory=all_staff_alert_events)
    quiet_hours: QuietHours | None = None


class UserNotificationPreferencesDocument(BaseDocument):
    """
    One cabinet user's preferences for the notifications of one business on
    their devices (Web Push). Without a document, every event arrives at
    any hour.
    """

    id: NotificationPreferencesId
    business_id: BusinessId
    user_id: UserId
    preferences: StaffNotificationPreferences = Field(
        default_factory=StaffNotificationPreferences
    )
