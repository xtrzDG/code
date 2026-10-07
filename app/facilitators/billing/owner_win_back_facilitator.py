import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.notification_utilities import StaffLinkSignerContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.subscription_lifecycle import OwnerWinBackFacilitatorContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.constants.subscription_lifecycle import WinBackStage
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.domain.users import UserDocument
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.notifications.staff_links import StaffLinkClaims
from app.schemas.dto.win_back_messages import WinBackMessage
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.constrained_strings import (
    CabinetDeepLink,
    StaffAlertSubject,
)
from app.schemas.typings.subscription_lifecycle.constrained_integers import (
    WinBackRecipientCount,
)
from app.utilities.billing.win_back_texts import (
    CONVERSATIONS_LINE,
    KEPT_LINE,
    REASON_HINTS,
    WIN_BACK_TITLES,
)
from app.utilities.notifications.cabinet_links import build_cabinet_link, link_expiry

logger: logging.Logger = logging.getLogger(__name__)


class OwnerWinBackFacilitator(OwnerWinBackFacilitatorContract):
    """
    Sends a win-back message through the outbox, like the owners' billing
    notices (retries, delivery state, hourly caps):

    - to every owner at their sign-in address: e-mail, or WhatsApp for an
      owner who signed in by phone, in their cabinet language;
    - to the business's Telegram chats linked to the platform bot (the
      owner's messenger in most small businesses), in the chat's language.

    The text names how many customers wrote since the cancellation, says
    everything set up is kept, adds the second message's hint for the
    reason given, and ends with a signed link to the billing page. Each
    stage reaches each address once (its outbox ids derive from the
    subscription and the stage). One failing recipient never stops the
    others.
    """

    def __init__(
        self,
        user_repo: UserRepoContract,
        manager_notifier: ManagerNotificationFacilitatorContract,
        link_signer: StaffLinkSignerContract,
        localized_text_resolver: LocalizedTextResolverContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._user_repo: UserRepoContract = user_repo
        self._manager_notifier: ManagerNotificationFacilitatorContract = (
            manager_notifier
        )
        self._link_signer: StaffLinkSignerContract = link_signer
        self._resolver: LocalizedTextResolverContract = localized_text_resolver
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def send(
        self, business: BusinessDocument, message: WinBackMessage
    ) -> WinBackRecipientCount:
        link: CabinetDeepLink | None = build_cabinet_link(
            self._link_signer,
            self._app_settings.cabinet_base_url,
            StaffLinkClaims(
                business_id=business.id,
                target=StaffLinkTarget.BILLING,
                expires_at=link_expiry(self._wall_clock.now_unix()),
            ),
        )
        subject = StaffAlertSubject(
            f"win_back:{message.subscription_id}_{message.stage.value}"
        )
        queued: int = 0
        for contact in self._contacts(business):
            try:
                queued += int(
                    self._manager_notifier.notify(
                        StaffNotification(
                            business_id=business.id,
                            contact=contact,
                            text=self._text(business, message, contact.language, link),
                            subject=subject,
                        )
                    )
                )
            except Exception:
                logger.exception(
                    "A win-back message by %s was not queued.", contact.channel.value
                )

        return WinBackRecipientCount(queued)

    def _contacts(self, business: BusinessDocument) -> list[ManagerContact]:
        contacts: list[ManagerContact] = [
            contact
            for contact in business.manager_contacts
            if contact.channel is ManagerContactChannel.TELEGRAM
        ]
        for member in business.members:
            if member.role is not BusinessMemberRole.OWNER:
                continue

            owner: UserDocument | None = self._user_repo.get(member.user_id)
            if owner is not None:
                contact: ManagerContact | None = _owner_contact(owner, business)
                if contact is not None:
                    contacts.append(contact)

        return contacts

    def _text(
        self,
        business: BusinessDocument,
        message: WinBackMessage,
        language: LanguageTag,
        link: CabinetDeepLink | None,
    ) -> MessageText:
        values: dict[str, str] = {
            "business": str(business.name),
            "count": str(int(message.conversations_since)),
        }
        lines: list[str] = [self._say(WIN_BACK_TITLES[message.stage], language, values)]
        lines.append("")
        if int(message.conversations_since) > 0:
            lines.append(self._say(CONVERSATIONS_LINE, language, values))

        lines.append(self._say(KEPT_LINE, language, values))
        hint: LocalizedText | None = (
            None if message.reason is None else REASON_HINTS.get(message.reason)
        )
        if message.stage is WinBackStage.DAY_30 and hint is not None:
            lines.append(self._say(hint, language, values))

        if link is not None:
            lines.extend(["", str(link)])

        return MessageText("\n".join(lines))

    def _say(
        self, text: LocalizedText, language: LanguageTag, values: dict[str, str]
    ) -> str:
        resolved: str = str(self._resolver.resolve(text, language))
        for name, value in values.items():
            resolved = resolved.replace("{" + name + "}", value)

        return resolved


def _owner_contact(
    owner: UserDocument, business: BusinessDocument
) -> ManagerContact | None:
    """An owner at their sign-in identity, in their cabinet language."""

    name = ManagerName(str(owner.display_name or business.name))
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
            channel=ManagerContactChannel.WHATSAPP,
            address=ManagerContactAddress(str(owner.phone_number)),
            language=owner.locale,
        )

    return None
