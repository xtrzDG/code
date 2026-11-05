import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.notification_utilities import StaffLinkSignerContract
from app.contracts.notifications import StaffAlertTextsContract
from app.contracts.owner_emails import OwnerAccountEmailFacilitatorContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.notifications import StaffTextStyle
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.domain.users import UserDocument
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.dto.notifications.staff_alerts import (
    StaffAlert,
    StaffNotificationTextInput,
)
from app.schemas.dto.notifications.staff_links import StaffLinkClaims
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.constrained_integers import (
    DeliveredNotificationCount,
)
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.notifications.constrained_strings import CabinetDeepLink
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.notifications.cabinet_links import build_cabinet_link, link_expiry

logger: logging.Logger = logging.getLogger(__name__)


class OwnerAccountEmailFacilitator(OwnerAccountEmailFacilitatorContract):
    """
    A notice every owner must get whatever they set up (PAY-06: the pages
    guests pay deposits on changed): the alert's brief (title and line,
    nothing about a customer) and a signed link to its page, valid for 7
    days and opened only after sign-in, sent through the outbox to the
    e-mail address each owner signs in with, in their account's language.
    Owners who sign in by phone have no address and hear it on their
    devices and the staff contacts only. One failing owner never stops the
    others.
    """

    def __init__(
        self,
        user_repo: UserRepoContract,
        manager_notifier: ManagerNotificationFacilitatorContract,
        link_signer: StaffLinkSignerContract,
        text_transformer: TransformerContract[StaffNotificationTextInput, MessageText],
        cabinet_base_url: CabinetBaseUrl | None,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._user_repo: UserRepoContract = user_repo
        self._manager_notifier: ManagerNotificationFacilitatorContract = (
            manager_notifier
        )
        self._link_signer: StaffLinkSignerContract = link_signer
        self._text_transformer: TransformerContract[
            StaffNotificationTextInput, MessageText
        ] = text_transformer
        self._cabinet_base_url: CabinetBaseUrl | None = cabinet_base_url
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def email_owners(
        self,
        business: BusinessDocument,
        alert: StaffAlert,
        texts: StaffAlertTextsContract,
    ) -> DeliveredNotificationCount:
        link: CabinetDeepLink | None = build_cabinet_link(
            self._link_signer,
            self._cabinet_base_url,
            StaffLinkClaims(
                business_id=business.id,
                target=alert.target,
                expires_at=link_expiry(self._wall_clock.now_unix()),
            ),
        )
        staff_addresses: set[str] = {
            str(contact.address).casefold()
            for contact in business.manager_contacts
            if contact.channel is ManagerContactChannel.EMAIL
        }
        queued: int = 0
        for member in business.members:
            if member.role is not BusinessMemberRole.OWNER:
                continue

            try:
                queued += self._email_owner(
                    business, member.user_id, alert, texts, link, staff_addresses
                )
            except Exception:
                logger.exception("An owner e-mail of business %s failed.", business.id)

        return DeliveredNotificationCount(queued)

    def _email_owner(
        self,
        business: BusinessDocument,
        user_id: UserId,
        alert: StaffAlert,
        texts: StaffAlertTextsContract,
        link: CabinetDeepLink | None,
        staff_addresses: set[str],
    ) -> int:
        owner: UserDocument | None = self._user_repo.get(user_id)
        if (
            owner is None
            or owner.email is None
            or str(owner.email).casefold() in staff_addresses
        ):
            return 0

        text: MessageText = self._text_transformer.transform(
            StaffNotificationTextInput(
                style=StaffTextStyle.BRIEF,
                language=owner.locale,
                brief=texts.brief(owner.locale),
                link=link,
            )
        )
        is_queued: bool = self._manager_notifier.notify(
            StaffNotification(
                business_id=business.id,
                contact=ManagerContact(
                    name=ManagerName(str(owner.display_name or owner.email)),
                    channel=ManagerContactChannel.EMAIL,
                    address=ManagerContactAddress(str(owner.email)),
                    language=owner.locale,
                ),
                text=text,
                subject=alert.subject,
            )
        )
        return 1 if is_queued else 0
