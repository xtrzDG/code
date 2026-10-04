import logging
from collections.abc import Sequence

from typed_time_provider import Microseconds, WallClock

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.notification_utilities import StaffLinkSignerContract
from app.contracts.notifications import StaffAlertFacilitatorContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.support_access import SignInNoticeFacilitatorContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.notifications import StaffLinkTarget, StaffTextStyle
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.domain.users import UserDocument, UserSessionDocument
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.dto.notifications.staff_alerts import (
    StaffAlert,
    StaffNotificationTextInput,
)
from app.schemas.dto.notifications.staff_links import StaffLinkClaims
from app.schemas.dto.sessions import SessionDevice
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.notifications.constrained_strings import (
    PushNotificationTag,
    StaffAlertSubject,
)
from app.utilities.notifications.cabinet_links import build_cabinet_link, link_expiry
from app.utilities.security.sign_in_notice_texts import SignInNoticeTexts
from app.utilities.security.user_agents import describe_device, is_same_device

logger: logging.Logger = logging.getLogger(__name__)

# A device subscribed in several businesses shows one notice (same tag).
MAX_NOTIFIED_BUSINESSES: int = 3


class SignInNoticeFacilitator(SignInNoticeFacilitatorContract):
    """
    Tells a person their account was signed in from a new device: a
    browser and system none of their other live sessions uses. A first
    sign-in (no other session) or a known device tells nobody.

    - Their devices with notifications on hear it through the staff alert
      facilitator as a personal, urgent alert (no staff contact, no quiet
      hours), in each business they belong to (owned ones first, at most
      three: one device shows it once, by its tag).
    - People who sign in by e-mail also get it by e-mail through the
      outbox, once.

    Every notice links to Account → Security, where the session is ended.
    Never raises.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        staff_alerts: StaffAlertFacilitatorContract,
        manager_notifier: ManagerNotificationFacilitatorContract,
        text_transformer: TransformerContract[StaffNotificationTextInput, MessageText],
        link_signer: StaffLinkSignerContract,
        localized_text_resolver: LocalizedTextResolverContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._staff_alerts: StaffAlertFacilitatorContract = staff_alerts
        self._manager_notifier: ManagerNotificationFacilitatorContract = (
            manager_notifier
        )
        self._text_transformer: TransformerContract[
            StaffNotificationTextInput, MessageText
        ] = text_transformer
        self._link_signer: StaffLinkSignerContract = link_signer
        self._resolver: LocalizedTextResolverContract = localized_text_resolver
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def notice_new_device(
        self,
        user: UserDocument,
        session: UserSessionDocument,
        other_sessions: Sequence[UserSessionDocument],
    ) -> None:
        try:
            device: SessionDevice = describe_device(session.user_agent)
            if not other_sessions or any(
                is_same_device(device, describe_device(other.user_agent))
                for other in other_sessions
            ):
                return

            self._notify(user, session, device)
        except Exception:
            logger.exception("The new-device notice of user %s failed.", user.id)

    def _notify(
        self, user: UserDocument, session: UserSessionDocument, device: SessionDevice
    ) -> None:
        businesses: list[BusinessDocument] = sorted(
            self._business_repo.list_by_member(user.id),
            key=lambda business: not is_owner(business, user),
        )[:MAX_NOTIFIED_BUSINESSES]
        if not businesses:
            return

        texts = SignInNoticeTexts(self._resolver, device, session.created_ip)
        subject = StaffAlertSubject(f"sign-in:{session.id}")
        for business in businesses:
            self._staff_alerts.alert(
                business,
                StaffAlert(
                    business_id=business.id,
                    target=StaffLinkTarget.ACCOUNT_SECURITY,
                    tag=PushNotificationTag(f"sign-in:{session.id}"),
                    subject=subject,
                    is_urgent=True,
                    recipient_user_ids=[user.id],
                ),
                texts,
            )

        if user.email is not None:
            self._email(user, businesses[0], texts, subject)

    def _email(
        self,
        user: UserDocument,
        business: BusinessDocument,
        texts: SignInNoticeTexts,
        subject: StaffAlertSubject,
    ) -> None:
        contact = ManagerContact(
            name=ManagerName(str(user.display_name or user.email)),
            channel=ManagerContactChannel.EMAIL,
            address=ManagerContactAddress(str(user.email)),
            language=user.locale,
        )
        link = build_cabinet_link(
            self._link_signer,
            self._app_settings.cabinet_base_url,
            StaffLinkClaims(
                business_id=business.id,
                target=StaffLinkTarget.ACCOUNT_SECURITY,
                expires_at=link_expiry(self._wall_clock.now_unix()),
            ),
        )
        self._manager_notifier.notify(
            StaffNotification(
                business_id=business.id,
                contact=contact,
                text=self._text_transformer.transform(
                    StaffNotificationTextInput(
                        style=StaffTextStyle.BRIEF,
                        language=user.locale,
                        brief=texts.brief(user.locale),
                        link=link,
                    )
                ),
                subject=subject,
            )
        )


def is_owner(business: BusinessDocument, user: UserDocument) -> bool:
    return any(
        member.user_id == user.id and member.role is BusinessMemberRole.OWNER
        for member in business.members
    )
