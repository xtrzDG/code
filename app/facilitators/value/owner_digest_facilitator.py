import logging
from zoneinfo import ZoneInfo

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
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.domain.notification_preferences import (
    UserNotificationPreferencesDocument,
)
from app.schemas.domain.users import UserDocument
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.dto.notifications.staff_alerts import PushNotification
from app.schemas.dto.notifications.staff_links import StaffLinkClaims
from app.schemas.dto.value.value_digests import ValueDigestText, ValueDigestTextInput
from app.schemas.dto.value.value_reports import ValueReportView
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
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
from app.utilities.value.digest_choices import wants_report

logger: logging.Logger = logging.getLogger(__name__)


class OwnerDigestFacilitator(OwnerDigestFacilitatorContract):
    """
    Sends the owners' digests and monthly reports through the outbox, like
    staff notifications (retries, delivery state, hourly caps):

    - by e-mail to each owner's sign-in address (SMTP; written to the log
      outside production without it), in the language of their cabinet;
    - to each device the owner turned notifications on for this business
      (Web Push), in the language of the device, held through the owner's
      quiet hours.

    The link opens the report, where its reader also turns the summaries
    off. Each report reaches each address and device once (its outbox id
    derives from the report). One failing recipient never stops the others.
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
                if wants_report(
                    self._digest_preferences_repo.get(business.id, member.user_id),
                    report.kind,
                ):
                    user: UserDocument | None = self._user_repo.get(member.user_id)
                    if user is not None:
                        queued += self._send_to_owner(business, user, report, link, now)
            except Exception:
                logger.exception("A value report for an owner was not queued.")

        return DigestRecipientCount(queued)

    def _send_to_owner(
        self,
        business: BusinessDocument,
        user: UserDocument,
        report: ValueReportView,
        link: CabinetDeepLink | None,
        now: Microseconds,
    ) -> int:
        subject = StaffAlertSubject(f"value_report:{report.id}")
        queued: int = 0
        if user.email is not None:
            text: ValueDigestText = self._text(business, report, user.locale, link)
            is_queued: bool = self._manager_notifier.notify(
                StaffNotification(
                    business_id=business.id,
                    contact=ManagerContact(
                        name=ManagerName(str(user.display_name or user.email)),
                        channel=ManagerContactChannel.EMAIL,
                        address=ManagerContactAddress(str(user.email)),
                        language=user.locale,
                    ),
                    text=text.message,
                    subject=subject,
                )
            )
            queued += int(is_queued)

        zone: ZoneInfo = load_time_zone(business.timezone)
        stored: UserNotificationPreferencesDocument | None = (
            self._notification_preferences_repo.get(business.id, user.id)
        )
        held_until: Microseconds | None = quiet_hours_end(
            None if stored is None else stored.preferences.quiet_hours, zone, now
        )
        for device in self._push_subscription_repo.list_by_user(business.id, user.id):
            brief = self._text(business, report, device.language, link).brief
            queued += int(
                self._push_queue.queue(
                    PushNotification(
                        business_id=business.id,
                        subscription_id=device.id,
                        user_id=user.id,
                        brief=brief,
                        link=link,
                        tag=PushNotificationTag(f"value_report:{report.kind.value}"),
                        subject=subject,
                        deliver_after=held_until,
                    )
                )
            )

        return queued

    def _text(
        self,
        business: BusinessDocument,
        report: ValueReportView,
        language: LanguageTag,
        link: CabinetDeepLink | None,
    ) -> ValueDigestText:
        return self._text_transformer.transform(
            ValueDigestTextInput(
                business_name=business.name,
                language=language,
                report=report,
                link=link,
            )
        )
