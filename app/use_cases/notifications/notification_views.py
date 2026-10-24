"""The views of Settings → Notifications, built from stored documents."""

from app.contracts.repositories.notification_repositories import (
    PushSubscriptionRepoContract,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.domain.notification_preferences import (
    StaffNotificationPreferences,
    UserNotificationPreferencesDocument,
)
from app.schemas.domain.push_subscriptions import PushSubscriptionDocument
from app.schemas.domain.staff_deliveries import StaffDeliveryStateDocument
from app.schemas.dto.notifications.notification_settings import (
    MyNotificationSettingsView,
    NotificationContactView,
    PushDeviceCommand,
    PushDeviceView,
    StaffDeliveryView,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.notifications.constrained_strings import (
    NotificationContactKey,
    VapidPublicKey,
)
from app.schemas.typings.notifications.prefixed_id import StaffDeliveryStateId
from app.utilities.deliveries.delivery_keys import staff_recipient_key
from app.utilities.notifications.staff_delivery_keys import (
    notification_contact_key,
    staff_delivery_state_id,
)
from app.utilities.notifications.staff_providers import is_provider_configured


def contact_key_of(
    business: BusinessDocument,
    contact: ManagerContact,
) -> NotificationContactKey:
    return notification_contact_key(business.id, contact.channel, str(contact.address))


def find_contact(
    business: BusinessDocument,
    contact_key: NotificationContactKey,
) -> ManagerContact:
    """The business's contact with this key; NotFoundError otherwise."""

    for contact in business.manager_contacts:
        if contact_key_of(business, contact) == contact_key:
            return contact

    raise NotFoundError("Notification contact was not found.")


def delivery_state_id_of(
    business: BusinessDocument,
    contact: ManagerContact,
) -> StaffDeliveryStateId:
    return staff_delivery_state_id(business.id, staff_recipient_key(contact))


def delivery_of_state(state: StaffDeliveryStateDocument) -> StaffDeliveryView:
    return StaffDeliveryView(
        status=state.status,
        last_error=state.last_error,
        attempted_at=state.attempted_at,
        delivered_at=state.delivered_at,
    )


def contact_view(
    business: BusinessDocument,
    contact: ManagerContact,
    state: StaffDeliveryStateDocument | None,
    settings: AppSettings,
) -> NotificationContactView:
    return NotificationContactView(
        key=contact_key_of(business, contact),
        name=contact.name,
        channel=contact.channel,
        address=contact.address,
        telegram_username=contact.telegram_username,
        language=contact.language,
        preferences=contact.preferences or StaffNotificationPreferences(),
        provider_ready=is_provider_configured(settings, contact.channel),
        delivery=None if state is None else delivery_of_state(state),
    )


def device_view(subscription: PushSubscriptionDocument) -> PushDeviceView:
    return PushDeviceView(
        id=subscription.id,
        language=subscription.language,
        created_at=subscription.created_at,
        delivered_at=subscription.delivered_at,
        last_error=subscription.last_error,
    )


def settings_view(
    business: BusinessDocument,
    stored: UserNotificationPreferencesDocument | None,
    devices: list[PushSubscriptionDocument],
    push_public_key: VapidPublicKey | None,
) -> MyNotificationSettingsView:
    return MyNotificationSettingsView(
        business_id=business.id,
        preferences=(
            StaffNotificationPreferences() if stored is None else stored.preferences
        ),
        push_public_key=push_public_key,
        devices=[
            device_view(device)
            for device in sorted(devices, key=lambda item: int(item.created_at))
        ],
    )


def require_own_device(
    push_subscription_repo: PushSubscriptionRepoContract,
    business: BusinessDocument,
    command: PushDeviceCommand,
) -> PushSubscriptionDocument:
    """The signed-in user's device; another user's is reported as missing."""

    device: PushSubscriptionDocument | None = push_subscription_repo.get(
        business.id, command.subscription_id
    )
    if device is None or device.user_id != command.user_id:
        raise NotFoundError("Device was not found.")

    return device
