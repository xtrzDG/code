import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.notification_utilities import StaffLinkSignerContract
from app.contracts.notifications import StaffAlertFacilitatorContract
from app.contracts.privacy import ExportDownloadNoticeFacilitatorContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.notifications import StaffLinkTarget, StaffTextStyle
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.domain.users import UserDocument
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.dto.notifications.staff_alerts import (
    StaffAlert,
    StaffNotificationTextInput,
)
from app.schemas.dto.notifications.staff_links import StaffLinkClaims
from app.schemas.dto.privacy.business_exports import ExportDownloadNotice
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.notifications.constrained_strings import (
    PushNotificationTag,
    StaffAlertSubject,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.notifications.cabinet_links import build_cabinet_link, link_expiry
from app.utilities.privacy.export_download_notice_texts import (
    ExportDownloadNoticeTexts,
    person_label,
)
from app.utilities.security.user_agents import describe_device

logger: logging.Logger = logging.getLogger(__name__)


class ExportDownloadNoticeFacilitator(ExportDownloadNoticeFacilitatorContract):
    """
    Tells every owner of a business that its full export was downloaded:
    who, from which browser and address, which download of the three.

    - Their devices with notifications on hear it through the staff alert
      facilitator as a personal, urgent alert (no staff contact, no quiet
      hours).
    - Each owner also gets it once through the outbox: by e-mail, or by
      SMS when they sign in by phone.

    Every notice links to Settings → Privacy. Never raises: the download
    itself is already audited.
    """

    def __init__(
        self,
        user_repo: UserRepoContract,
        staff_alerts: StaffAlertFacilitatorContract,
        manager_notifier: ManagerNotificationFacilitatorContract,
        text_transformer: TransformerContract[StaffNotificationTextInput, MessageText],
        link_signer: StaffLinkSignerContract,
        localized_text_resolver: LocalizedTextResolverContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._user_repo: UserRepoContract = user_repo
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

    def notice_download(
        self, business: BusinessDocument, notice: ExportDownloadNotice
    ) -> None:
        try:
            self._notify(business, notice)
        except Exception:
            logger.exception(
                "The export download notice of business %s failed.", business.id
            )

    def _notify(self, business: BusinessDocument, notice: ExportDownloadNotice) -> None:
        owner_ids: list[UserId] = [
            member.user_id
            for member in business.members
            if member.role is BusinessMemberRole.OWNER
        ]
        texts = ExportDownloadNoticeTexts(
            self._resolver,
            self._user_repo.get(notice.downloaded_by),
            describe_device(notice.user_agent),
            notice.client_ip_address,
            notice.download_number,
        )
        key: str = f"{notice.export_id}-{int(notice.download_number)}"
        subject = StaffAlertSubject(f"export_download:{key}")
        self._staff_alerts.alert(
            business,
            StaffAlert(
                business_id=business.id,
                target=StaffLinkTarget.PRIVACY,
                tag=PushNotificationTag(f"export_download:{key}"),
                subject=subject,
                is_urgent=True,
                recipient_user_ids=owner_ids,
            ),
            texts,
        )
        for owner in self._user_repo.get_many(owner_ids):
            self._message(owner, business, texts, subject)

    def _message(
        self,
        owner: UserDocument,
        business: BusinessDocument,
        texts: ExportDownloadNoticeTexts,
        subject: StaffAlertSubject,
    ) -> None:
        contact: ManagerContact | None = personal_contact(owner)
        if contact is None:
            return

        link = build_cabinet_link(
            self._link_signer,
            self._app_settings.cabinet_base_url,
            StaffLinkClaims(
                business_id=business.id,
                target=StaffLinkTarget.PRIVACY,
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
                        language=owner.locale,
                        brief=texts.brief(owner.locale),
                        link=link,
                    )
                ),
                subject=subject,
            )
        )


def personal_contact(owner: UserDocument) -> ManagerContact | None:
    """The owner's own e-mail, else their phone by SMS; None without either."""

    name = ManagerName(person_label(owner) or "Owner")
    if owner.email is not None:
        return ManagerContact(
            name=name,
            channel=ManagerContactChannel.EMAIL,
            address=ManagerContactAddress(str(owner.email)),
            language=owner.locale,
        )
    if owner.phone_number is not None:
        return ManagerContact(
            name=name,
            channel=ManagerContactChannel.SMS,
            address=ManagerContactAddress(str(owner.phone_number)),
            language=owner.locale,
        )
    return None
