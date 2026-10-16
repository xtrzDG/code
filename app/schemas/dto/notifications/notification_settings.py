"""
Settings → Notifications: the staff contacts with how delivery to them
goes, one user's preferences and devices, and notification tests.
"""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.deliveries import OutboundMessageStatus
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.notifications import StaffAlertEvent
from app.schemas.domain.notification_preferences import (
    QuietHours,
    StaffNotificationPreferences,
)
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.domain.push_subscriptions import PushSubscriptionKeys
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.deliveries.strings import DeliveryErrorText
from app.schemas.typings.handoffs.constrained_strings import ManagerTelegramUsername
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.booleans import (
    IsDeliverySimulated,
    IsProviderReady,
)
from app.schemas.typings.notifications.constrained_strings import (
    NotificationContactKey,
    PushEndpointUrl,
    VapidPublicKey,
)
from app.schemas.typings.notifications.prefixed_id import PushSubscriptionId
from app.schemas.typings.users.prefixed_id import UserId


class StaffDeliveryView(ImmutableDTO):
    """
    How the latest notification to a contact or device went: sending
    (`pending`, also while held for quiet hours or waiting for a retry),
    `delivered` or `dead` with the reason, and when one last arrived.
    """

    status: OutboundMessageStatus
    last_error: DeliveryErrorText | None = None
    attempted_at: Microseconds
    delivered_at: Microseconds | None = None


class NotificationContactView(ImmutableDTO):
    """
    A staff contact as Settings shows it. `provider_ready` is False when
    this server has no provider for its channel (then notifications fail
    in production and are only logged elsewhere); `delivery` is None until
    a first notification.
    """

    key: NotificationContactKey
    name: ManagerName
    channel: ManagerContactChannel
    address: ManagerContactAddress
    telegram_username: ManagerTelegramUsername | None = None
    language: LanguageTag
    preferences: StaffNotificationPreferences
    provider_ready: IsProviderReady
    delivery: StaffDeliveryView | None = None


class NotificationContactList(ImmutableDTO):
    business_id: BusinessId
    items: list[NotificationContactView]


class NotificationContactsQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId


class ContactCheckCommand(ImmutableDTO):
    """The owner sends a test notification to one contact."""

    user_id: UserId
    business_id: BusinessId
    contact_key: NotificationContactKey
    client_ip_address: ClientIpAddress | None = None


class PushDeviceView(ImmutableDTO):
    """One device of the signed-in user that shows notifications."""

    id: PushSubscriptionId
    language: LanguageTag
    created_at: Microseconds
    delivered_at: Microseconds | None = None
    last_error: DeliveryErrorText | None = None


class MyNotificationSettingsView(ImmutableDTO):
    """
    The signed-in user's notifications in one business: which events and
    quiet hours, the devices that show them, and the key a browser
    subscribes with (None: device notifications are off on this server).
    """

    business_id: BusinessId
    preferences: StaffNotificationPreferences
    push_public_key: VapidPublicKey | None = None
    devices: list[PushDeviceView]


class NotificationSettingsQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId


class NotificationPreferencesRequest(ImmutableDTO):
    """HTTP body: which events reach me, and my quiet hours (None: none)."""

    events: list[StaffAlertEvent]
    quiet_hours: QuietHours | None = None


class UpdateNotificationPreferencesCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    request: NotificationPreferencesRequest


class PushSubscriptionRequest(ImmutableDTO):
    """
    HTTP body: the browser's push subscription (PushSubscription.toJSON())
    and the cabinet's language, which its notifications will speak.
    """

    endpoint: PushEndpointUrl
    keys: PushSubscriptionKeys
    language: LanguageTag


class SubscribePushCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    request: PushSubscriptionRequest


class PushDeviceCommand(ImmutableDTO):
    """One of the signed-in user's own devices (turn off, test)."""

    user_id: UserId
    business_id: BusinessId
    subscription_id: PushSubscriptionId


class NotificationCheckQueued(ImmutableDTO):
    """
    A test notification stored in the outbox (DEAD at once when it cannot
    be delivered); `is_simulated` when no provider is set outside
    production and it is only written to the log.
    """

    message: OutboundMessageDocument
    is_simulated: IsDeliverySimulated = False


class NotificationCheckResult(ImmutableDTO):
    """How a test notification went right after it was sent."""

    delivery: StaffDeliveryView
    is_simulated: IsDeliverySimulated = False
