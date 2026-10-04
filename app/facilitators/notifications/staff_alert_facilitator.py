import logging
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds, WallClock

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.notification_utilities import StaffLinkSignerContract
from app.contracts.notifications import (
    PushNotificationQueueContract,
    StaffAlertFacilitatorContract,
    StaffAlertTextsContract,
)
from app.contracts.repositories.notification_repositories import (
    NotificationPreferencesRepoContract,
    PushSubscriptionRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.notifications import StaffTextStyle
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.domain.notification_preferences import (
    StaffNotificationPreferences,
    UserNotificationPreferencesDocument,
)
from app.schemas.domain.push_subscriptions import PushSubscriptionDocument
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.dto.notifications.staff_alerts import (
    PushNotification,
    StaffAlert,
    StaffNotificationTextInput,
)
from app.schemas.dto.notifications.staff_links import StaffLinkClaims
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.constrained_integers import (
    DeliveredNotificationCount,
)
from app.schemas.typings.notifications.constrained_strings import CabinetDeepLink
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.notifications.cabinet_links import build_cabinet_link, link_expiry
from app.utilities.notifications.quiet_hours import quiet_hours_end
from app.utilities.scheduling.zoned_time import load_time_zone

logger: logging.Logger = logging.getLogger(__name__)

# Chats the staff member linked themselves may show the customer's details.
DETAILED_CHANNELS: frozenset[ManagerContactChannel] = frozenset(
    {ManagerContactChannel.TELEGRAM, ManagerContactChannel.WHATSAPP}
)
DEFAULT_PREFERENCES: StaffNotificationPreferences = StaffNotificationPreferences()


class StaffAlertFacilitator(StaffAlertFacilitatorContract):
    """
    Tells staff about a handoff, request or booking on every channel.

    - Staff contacts (Telegram, WhatsApp, e-mail, SMS) that want this
      event, each in their language: linked chats get the detailed text,
      e-mail and SMS the brief (no customer details); every text ends with
      a signed link to the page, valid for 7 days and opened only after
      sign-in.
    - The devices of the business's members (Web Push) that want this
      event: title, line and link in the language each device was turned
      on in. A device of someone no longer in the team is removed.
    - Quiet hours (in the business time zone) hold a notification until
      they end; urgent handoffs come through.
    - An alert that names a subject (a call's summary) reaches each
      recipient once, however often it is raised; one that names contact
      channels skips the staff contacts of other channels; a personal one
      (`recipient_user_ids`) reaches only those users' devices.

    One failing recipient never stops the others. Never raises.
    """

    def __init__(
        self,
        manager_notifier: ManagerNotificationFacilitatorContract,
        push_queue: PushNotificationQueueContract,
        push_subscription_repo: PushSubscriptionRepoContract,
        notification_preferences_repo: NotificationPreferencesRepoContract,
        link_signer: StaffLinkSignerContract,
        text_transformer: TransformerContract[StaffNotificationTextInput, MessageText],
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._manager_notifier: ManagerNotificationFacilitatorContract = (
            manager_notifier
        )
        self._push_queue: PushNotificationQueueContract = push_queue
        self._push_subscription_repo: PushSubscriptionRepoContract = (
            push_subscription_repo
        )
        self._notification_preferences_repo: NotificationPreferencesRepoContract = (
            notification_preferences_repo
        )
        self._link_signer: StaffLinkSignerContract = link_signer
        self._text_transformer: TransformerContract[
            StaffNotificationTextInput, MessageText
        ] = text_transformer
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def alert(
        self,
        business: BusinessDocument,
        alert: StaffAlert,
        texts: StaffAlertTextsContract,
    ) -> DeliveredNotificationCount:
        now: Microseconds = self._wall_clock.now_unix()
        zone: ZoneInfo = load_time_zone(business.timezone)
        link: CabinetDeepLink | None = self._link(alert, now)
        queued: int = 0
        for contact in business.manager_contacts:
            try:
                queued += self._notify_contact(contact, alert, texts, link, zone, now)
            except Exception:
                logger.exception("Staff alert by %s failed.", contact.channel.value)

        try:
            queued += self._notify_devices(business, alert, texts, link, zone, now)
        except Exception:
            logger.exception("Device alerts of business %s failed.", business.id)

        return DeliveredNotificationCount(queued)

    def _notify_contact(
        self,
        contact: ManagerContact,
        alert: StaffAlert,
        texts: StaffAlertTextsContract,
        link: CabinetDeepLink | None,
        zone: ZoneInfo,
        now: Microseconds,
    ) -> int:
        preferences = contact.preferences or DEFAULT_PREFERENCES
        if (
            not is_wanted(alert, preferences)
            or alert.recipient_user_ids is not None
            or (
                alert.contact_channels is not None
                and contact.channel not in alert.contact_channels
            )
        ):
            return 0

        is_detailed: bool = contact.channel in DETAILED_CHANNELS
        text: MessageText = self._text_transformer.transform(
            StaffNotificationTextInput(
                style=StaffTextStyle.DETAILED if is_detailed else StaffTextStyle.BRIEF,
                language=contact.language,
                detailed=texts.detailed(contact.language) if is_detailed else None,
                brief=None if is_detailed else texts.brief(contact.language),
                link=link,
            )
        )
        is_queued: bool = self._manager_notifier.notify(
            StaffNotification(
                business_id=alert.business_id,
                contact=contact,
                text=text,
                handoff_id=alert.handoff_id,
                subject=alert.subject,
                deliver_after=self._held_until(alert, preferences, zone, now),
            )
        )
        return 1 if is_queued else 0

    def _notify_devices(
        self,
        business: BusinessDocument,
        alert: StaffAlert,
        texts: StaffAlertTextsContract,
        link: CabinetDeepLink | None,
        zone: ZoneInfo,
        now: Microseconds,
    ) -> int:
        members: set[UserId] = {member.user_id for member in business.members}
        preferences_by_user: dict[UserId, StaffNotificationPreferences] = {}
        queued: int = 0
        for subscription in self._push_subscription_repo.list_by_business(business.id):
            if subscription.user_id not in members:
                self._push_subscription_repo.delete(business.id, subscription.id)
                continue

            if (
                alert.recipient_user_ids is not None
                and subscription.user_id not in alert.recipient_user_ids
            ):
                continue

            preferences = preferences_by_user.get(subscription.user_id)
            if preferences is None:
                preferences = self._preferences_of(business, subscription.user_id)
                preferences_by_user[subscription.user_id] = preferences

            if is_wanted(alert, preferences) and self._push(
                subscription, alert, texts, link, preferences, zone, now
            ):
                queued += 1

        return queued

    def _push(
        self,
        subscription: PushSubscriptionDocument,
        alert: StaffAlert,
        texts: StaffAlertTextsContract,
        link: CabinetDeepLink | None,
        preferences: StaffNotificationPreferences,
        zone: ZoneInfo,
        now: Microseconds,
    ) -> bool:
        return self._push_queue.queue(
            PushNotification(
                business_id=alert.business_id,
                subscription_id=subscription.id,
                user_id=subscription.user_id,
                brief=texts.brief(subscription.language),
                link=link,
                tag=alert.tag,
                handoff_id=alert.handoff_id,
                subject=alert.subject,
                is_urgent=alert.is_urgent,
                deliver_after=self._held_until(alert, preferences, zone, now),
            )
        )

    def _preferences_of(
        self,
        business: BusinessDocument,
        user_id: UserId,
    ) -> StaffNotificationPreferences:
        stored: UserNotificationPreferencesDocument | None = (
            self._notification_preferences_repo.get(business.id, user_id)
        )
        return DEFAULT_PREFERENCES if stored is None else stored.preferences

    def _held_until(
        self,
        alert: StaffAlert,
        preferences: StaffNotificationPreferences,
        zone: ZoneInfo,
        now: Microseconds,
    ) -> Microseconds | None:
        if alert.is_urgent:
            return None

        return quiet_hours_end(preferences.quiet_hours, zone, now)

    def _link(self, alert: StaffAlert, now: Microseconds) -> CabinetDeepLink | None:
        return build_cabinet_link(
            self._link_signer,
            self._app_settings.cabinet_base_url,
            StaffLinkClaims(
                business_id=alert.business_id,
                target=alert.target,
                conversation_id=alert.conversation_id,
                lead_id=alert.lead_id,
                booking_id=alert.booking_id,
                expires_at=link_expiry(now),
            ),
        )


def is_wanted(alert: StaffAlert, preferences: StaffNotificationPreferences) -> bool:
    """The recipient chose the alert's event; news without an event always is."""

    return alert.event is None or alert.event in preferences.events
