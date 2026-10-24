"""
What every billing message to a business's owners shares (the win-back
messages, the notices of a declined charge's retries): its recipients, the
signed link to the billing page and the outbox it goes through.
"""

import logging
from collections.abc import Callable

from typed_time_provider import Microseconds, WallClock

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.notification_utilities import StaffLinkSignerContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.domain.users import UserDocument
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.notifications.staff_links import StaffLinkClaims
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.constrained_strings import (
    CabinetDeepLink,
    StaffAlertSubject,
)
from app.utilities.billing.owner_billing_contacts import (
    owner_contact,
    telegram_contacts,
)
from app.utilities.notifications.cabinet_links import build_cabinet_link, link_expiry

logger: logging.Logger = logging.getLogger(__name__)


class OwnerBillingNotices:
    """
    Sends one billing message through the outbox, like the owners' other
    billing notices (retries, delivery state, hourly caps):

    - to every owner at their sign-in address: e-mail, or WhatsApp for an
      owner who signed in by phone, in their cabinet language;
    - to the business's Telegram chats linked to the platform bot (the
      owner's messenger in most small businesses), in the chat's language.

    Every text ends with a signed link to the billing page. Each address
    gets the message once however often it is queued (its outbox ids derive
    from the subject); one failing recipient never stops the others.
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

    def notify_owners(
        self,
        business: BusinessDocument,
        subject: StaffAlertSubject,
        lines_in: Callable[[LanguageTag], list[str]],
        what: str,
    ) -> int:
        """
        Queue the message for every recipient: `lines_in` writes its lines
        in a recipient's language, the billing link follows them. Returns
        how many recipients it was queued for (`what` names it in the log).
        """

        link: CabinetDeepLink | None = build_cabinet_link(
            self._link_signer,
            self._app_settings.cabinet_base_url,
            StaffLinkClaims(
                business_id=business.id,
                target=StaffLinkTarget.BILLING,
                expires_at=link_expiry(self._wall_clock.now_unix()),
            ),
        )
        queued: int = 0
        for contact in self._contacts(business):
            try:
                lines: list[str] = lines_in(contact.language)
                if link is not None:
                    lines.extend(["", str(link)])
                queued += int(
                    self._manager_notifier.notify(
                        StaffNotification(
                            business_id=business.id,
                            contact=contact,
                            text=MessageText("\n".join(lines)),
                            subject=subject,
                        )
                    )
                )
            except Exception:
                logger.exception(
                    "%s by %s was not queued.", what, contact.channel.value
                )

        return queued

    def say(
        self, text: LocalizedText, language: LanguageTag, values: dict[str, str]
    ) -> str:
        """The text in `language` with its `{name}` placeholders filled in."""

        resolved: str = str(self._resolver.resolve(text, language))
        for name, value in values.items():
            resolved = resolved.replace("{" + name + "}", value)

        return resolved

    def _contacts(self, business: BusinessDocument) -> list[ManagerContact]:
        contacts: list[ManagerContact] = telegram_contacts(business)
        for member in business.members:
            if member.role is not BusinessMemberRole.OWNER:
                continue

            owner: UserDocument | None = self._user_repo.get(member.user_id)
            contact: ManagerContact | None = (
                None if owner is None else owner_contact(owner, business)
            )
            if contact is not None:
                contacts.append(contact)

        return contacts
