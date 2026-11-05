import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.notification_utilities import StaffLinkSignerContract
from app.contracts.notifications import PushNotificationQueueContract
from app.contracts.repositories.notification_repositories import (
    NotificationPreferencesRepoContract,
    PushSubscriptionRepoContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.repositories.value_repositories import (
    DigestPreferencesRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.value import OwnerDigestFacilitatorContract
from app.facilitators.value.owner_digest_messages import (
    OwnerReport,
    email_notification,
    owner_telegram_chat,
    telegram_notification,
    whatsapp_notification,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.constants.value import DigestChannel
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.notification_preferences import (
    UserNotificationPreferencesDocument,
)
from app.schemas.domain.users import UserDocument
from app.schemas.domain.value_settings import DigestPreferencesDocument
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.dto.notifications.staff_alerts import PushNotification
from app.schemas.dto.notifications.staff_links import StaffLinkClaims
from app.schemas.dto.value.value_digests import ValueDigestText, ValueDigestTextInput
from app.schemas.dto.value.value_reports import ValueReportView
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.constrained_strings import (
    CabinetDeepLink,
    PushNotificationTag,
    StaffAlertSubject,
)
from app.schemas.typings.value.constrained_integers import DigestRecipientCount
from app.utilities.notifications.cabinet_links import build_cabinet_link, link_expiry
from app.utilities.notifications.quiet_hours import quiet_hours_end
from app.utilities.scheduling.zoned_time import load_time_zone
from app.utilities.value.digest_choices import digest_channels_of, wants_report

logger: logging.Logger = logging.getLogger(__name__)


class OwnerDigestFacilitator(OwnerDigestFacilitatorContract):
    """
    Sends the owners' digests and monthly reports through the outbox, like
    staff notifications (retries, delivery state, hourly caps), to the
    channels each owner chose (`digest_channels_of`; e-mail and devices
    when they chose none):

    - EMAIL: their sign-in address (SMTP; written to the log outside
      production without it), in the language of their cabinet;
    - PUSH: each device they turned notifications on for this business
      (Web Push), in the language of the device;
    - TELEGRAM: their own chat among the business's chats linked to the
      platform bot, the whole report in the chat's language;
    - WHATSAPP: the number they opted in with, the report's summary in the
      approved owner report template from the platform number.

    Devices, Telegram and WhatsApp are held through the owner's quiet hours.
    The link opens the report, where its reader also turns the summaries
    off. Each report reaches each address, chat and device once (its outbox
    id derives from the report and the recipient), also when sent again.
    One failing recipient never stops the others.
    """

    def __init__(
        self,
        user_repo: UserRepoContract,
        digest_preferences_repo: DigestPreferencesRepoContract,
        push_subscription_repo: PushSubscriptionRepoContract,
        notification_preferences_repo: NotificationPreferencesRepoContract,
        manager_notifier: ManagerNotificationFacilitatorContract,
        push_queue: PushNotificationQueueContract,
        link_signer: StaffLinkSignerContract,
        text_transformer: TransformerContract[ValueDigestTextInput, ValueDigestText],
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._user_repo: UserRepoContract = user_repo
        self._digest_preferences_repo: DigestPreferencesRepoContract = (
            digest_preferences_repo
        )
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
        self._text_transformer: TransformerContract[
            ValueDigestTextInput, ValueDigestText
        ] = text_transformer
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def send(
        self,
        business: BusinessDocument,
        report: ValueReportView,
    ) -> DigestRecipientCount:
        now: Microseconds = self._wall_clock.now_unix()
        link: CabinetDeepLink | None = build_cabinet_link(
            self._link_signer,
            self._app_settings.cabinet_base_url,
            StaffLinkClaims(
                business_id=business.id,
                target=StaffLinkTarget.REPORT,
                value_report_id=report.id,
                expires_at=link_expiry(now),
            ),
        )
        queued: int = 0
        for member in business.members:
            if member.role is not BusinessMemberRole.OWNER:
                continue

            try:
                preferences: DigestPreferencesDocument | None = (
                    self._digest_preferences_repo.get(business.id, member.user_id)
                )
                user: UserDocument | None = self._user_repo.get(member.user_id)
                if user is not None and wants_report(preferences, report.kind):
                    owner = OwnerReport(business, user, preferences, report, link)
                    queued += self._send_to_owner(owner, now)
            except Exception:
                logger.exception("A value report for an owner was not queued.")

        return DigestRecipientCount(queued)

    def _send_to_owner(self, owner: OwnerReport, now: Microseconds) -> int:
        business, user = owner.business, owner.user
        subject = StaffAlertSubject(f"value_report:{owner.report.id}")
        stored: UserNotificationPreferencesDocument | None = (
            self._notification_preferences_repo.get(business.id, user.id)
        )
        held_until: Microseconds | None = quiet_hours_end(
            None if stored is None else stored.preferences.quiet_hours,
            load_time_zone(business.timezone),
            now,
        )
        notifications: list[StaffNotification | None] = []
        queued: int = 0
        for channel in digest_channels_of(owner.preferences):
            if channel is DigestChannel.EMAIL:
                text = self._text(owner, user.locale)
                notifications.append(email_notification(business, user, text, subject))
            elif channel is DigestChannel.PUSH:
                queued += self._send_to_devices(owner, subject, held_until)
            elif channel is DigestChannel.TELEGRAM:
                chat = owner_telegram_chat(business, owner.preferences)
                if chat is not None:
                    text = self._text(owner, chat.language)
                    notifications.append(
                        telegram_notification(business, chat, text, subject, held_until)
                    )
            else:
                notifications.append(
                    whatsapp_notification(
                        business,
                        user,
                        owner.preferences,
                        self._text(owner, user.locale),
                        owner.link,
                        self._app_settings,
                        (subject, held_until),
                    )
                )

        for notification in notifications:
            if notification is not None:
                queued += int(self._manager_notifier.notify(notification))

        return queued

    def _send_to_devices(
        self,
        owner: OwnerReport,
        subject: StaffAlertSubject,
        held_until: Microseconds | None,
    ) -> int:
        queued: int = 0
        business, user = owner.business, owner.user
        for device in self._push_subscription_repo.list_by_user(business.id, user.id):
            queued += int(
                self._push_queue.queue(
                    PushNotification(
                        business_id=business.id,
                        subscription_id=device.id,
                        user_id=user.id,
                        brief=self._text(owner, device.language).brief,
                        link=owner.link,
                        tag=PushNotificationTag(
                            f"value_report:{owner.report.kind.value}"
                        ),
                        subject=subject,
                        deliver_after=held_until,
                    )
                )
            )

        return queued

    def _text(self, owner: OwnerReport, language: LanguageTag) -> ValueDigestText:
        return self._text_transformer.transform(
            ValueDigestTextInput(
                business_name=owner.business.name,
                language=language,
                report=owner.report,
                link=owner.link,
            )
        )
