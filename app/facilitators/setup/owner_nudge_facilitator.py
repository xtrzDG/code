import logging
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds, WallClock

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.notification_utilities import StaffLinkSignerContract
from app.contracts.notifications import PushNotificationQueueContract
from app.contracts.nudges import OwnerNudgeFacilitatorContract
from app.contracts.repositories.notification_repositories import (
    NotificationPreferencesRepoContract,
    PushSubscriptionRepoContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.domain.notification_preferences import (
    UserNotificationPreferencesDocument,
)
from app.schemas.domain.users import UserDocument
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.dto.notifications.staff_alerts import (
    PushNotification,
    StaffAlertBrief,
)
from app.schemas.dto.notifications.staff_links import StaffLinkClaims
from app.schemas.dto.setup.nudges import NudgeMessage
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.constrained_strings import (
    CabinetDeepLink,
    PushNotificationTag,
    StaffAlertSubject,
)
from app.schemas.typings.notifications.strings import (
    StaffAlertDetail,
    StaffAlertTitle,
)
from app.schemas.typings.setup.constrained_integers import NudgeRecipientCount
from app.utilities.notifications.cabinet_links import build_cabinet_link, link_expiry
from app.utilities.notifications.quiet_hours import quiet_hours_end
from app.utilities.scheduling.zoned_time import load_time_zone
from app.utilities.setup.nudge_texts import (
    NUDGE_DETAILS,
    NUDGE_FOOTER,
    NUDGE_TARGETS,
    NUDGE_TITLES,
)

logger: logging.Logger = logging.getLogger(__name__)


class OwnerNudgeFacilitator(OwnerNudgeFacilitatorContract):
    """
    Sends an activation nudge through the outbox, like the owners' digests
    (retries, delivery state, hourly caps):

    - by e-mail to each owner's sign-in address, in their cabinet language;
    - to each device an owner turned notifications on for this business
      (Web Push), in the device's language, held through quiet hours;
    - to the business's Telegram chats linked to the platform bot (the
      owner's own chat in most small businesses), in the chat's language.

    Every text ends with a signed link to the page that finishes the step
    and says where the reminders are turned off. Each nudge reaches each
    address once (its outbox ids derive from the business and the nudge).
    One failing recipient never stops the others.
    """

    def __init__(
        self,
        user_repo: UserRepoContract,
        push_subscription_repo: PushSubscriptionRepoContract,
        notification_preferences_repo: NotificationPreferencesRepoContract,
        manager_notifier: ManagerNotificationFacilitatorContract,
        push_queue: PushNotificationQueueContract,
        link_signer: StaffLinkSignerContract,
        localized_text_resolver: LocalizedTextResolverContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._user_repo: UserRepoContract = user_repo
        self._push_subscription_repo: PushSubscriptionRepoContract = (
            push_subscription_repo
        )
        self._notification_preferences_repo: NotificationPreferencesRepoContract = (
            notification_preferences_repo
        )
        self._manager_notifier: ManagerNotificationFacilitatorContract = (
            manager_notifier
        )
        self._push_queue: PushNotificationQueueContract = push_queue
        self._link_signer: StaffLinkSignerContract = link_signer
        self._resolver: LocalizedTextResolverContract = localized_text_resolver
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def send(
        self,
        business: BusinessDocument,
        nudge: NudgeMessage,
    ) -> NudgeRecipientCount:
        now: Microseconds = self._wall_clock.now_unix()
        link: CabinetDeepLink | None = build_cabinet_link(
            self._link_signer,
            self._app_settings.cabinet_base_url,
            StaffLinkClaims(
                business_id=business.id,
                target=NUDGE_TARGETS[nudge.topic],
                expires_at=link_expiry(now),
            ),
        )
        subject = StaffAlertSubject(f"nudge:{nudge.code.value}")
        queued: int = 0
        for contact in business.manager_contacts:
            if contact.channel is not ManagerContactChannel.TELEGRAM:
                continue

            queued += self._notify(business, contact, nudge, link, subject)

        for member in business.members:
            if member.role is not BusinessMemberRole.OWNER:
                continue

            try:
                user: UserDocument | None = self._user_repo.get(member.user_id)
                if user is not None:
                    queued += self._send_to_owner(business, user, nudge, link, now)
            except Exception:
                logger.exception("A nudge for an owner was not queued.")

        return NudgeRecipientCount(queued)

    def _send_to_owner(
        self,
        business: BusinessDocument,
        user: UserDocument,
        nudge: NudgeMessage,
        link: CabinetDeepLink | None,
        now: Microseconds,
    ) -> int:
        subject = StaffAlertSubject(f"nudge:{nudge.code.value}")
        queued: int = 0
        if user.email is not None:
            email = ManagerContact(
                name=ManagerName(str(user.display_name or user.email)),
                channel=ManagerContactChannel.EMAIL,
                address=ManagerContactAddress(str(user.email)),
                language=user.locale,
            )
            queued += self._notify(business, email, nudge, link, subject)

        zone: ZoneInfo = load_time_zone(business.timezone)
        stored: UserNotificationPreferencesDocument | None = (
            self._notification_preferences_repo.get(business.id, user.id)
        )
        held_until: Microseconds | None = quiet_hours_end(
            None if stored is None else stored.preferences.quiet_hours, zone, now
        )
        for device in self._push_subscription_repo.list_by_user(business.id, user.id):
            queued += int(
                self._push_queue.queue(
                    PushNotification(
                        business_id=business.id,
                        subscription_id=device.id,
                        user_id=user.id,
                        brief=self._brief(business, nudge, device.language),
                        link=link,
                        tag=PushNotificationTag(f"nudge:{nudge.code.value}"),
                        subject=subject,
                        deliver_after=held_until,
                    )
                )
            )

        return queued

    def _notify(
        self,
        business: BusinessDocument,
        contact: ManagerContact,
        nudge: NudgeMessage,
        link: CabinetDeepLink | None,
        subject: StaffAlertSubject,
    ) -> int:
        try:
            return int(
                self._manager_notifier.notify(
                    StaffNotification(
                        business_id=business.id,
                        contact=contact,
                        text=self._text(business, nudge, contact.language, link),
                        subject=subject,
                    )
                )
            )
        except Exception:
            logger.exception("A nudge by %s was not queued.", contact.channel.value)
            return 0

    def _brief(
        self,
        business: BusinessDocument,
        nudge: NudgeMessage,
        language: LanguageTag,
    ) -> StaffAlertBrief:
        name: str = str(business.name)
        return StaffAlertBrief(
            title=StaffAlertTitle(
                self._resolver.resolve(NUDGE_TITLES[nudge.topic], language).replace(
                    "{name}", name
                )
            ),
            detail=StaffAlertDetail(
                self._resolver.resolve(NUDGE_DETAILS[nudge.topic], language)
            ),
        )

    def _text(
        self,
        business: BusinessDocument,
        nudge: NudgeMessage,
        language: LanguageTag,
        link: CabinetDeepLink | None,
    ) -> MessageText:
        brief: StaffAlertBrief = self._brief(business, nudge, language)
        lines: list[str] = [str(brief.title), "", str(brief.detail)]
        if link is not None:
            lines.append(str(link))

        lines.extend(["", self._resolver.resolve(NUDGE_FOOTER, language)])
        return MessageText("\n".join(lines))
