import logging

from babel.dates import format_date
from typed_time_provider import Microseconds, WallClock

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.notification_utilities import StaffLinkSignerContract
from app.contracts.payment_methods import DunningNoticeFacilitatorContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.constants.payments import DunningNoticeKind
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.domain.users import UserDocument
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.notifications.staff_links import StaffLinkClaims
from app.schemas.dto.payment_retries import DunningNotice
from app.schemas.typings.billing.constrained_integers import DunningRecipientCount
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.notifications.constrained_strings import (
    CabinetDeepLink,
    StaffAlertSubject,
)
from app.utilities.billing.billing_periods import to_local_datetime
from app.utilities.billing.dunning_texts import DUNNING_TEXTS, FULL_SERVICE_DEADLINE
from app.utilities.billing.owner_billing_contacts import (
    owner_contact,
    telegram_contacts,
)
from app.utilities.localization.babel_locales import require_babel_locale
from app.utilities.money.money_formatting import format_money
from app.utilities.notifications.cabinet_links import build_cabinet_link, link_expiry

logger: logging.Logger = logging.getLogger(__name__)
DATE_FORMAT: str = "long"


class DunningNoticeFacilitator(DunningNoticeFacilitatorContract):
    """
    Tells the owners how a retry of a declined automatic charge went,
    through the outbox like their other billing notices (retries, delivery
    state, hourly caps):

    - to every owner at their sign-in address (e-mail, or WhatsApp for an
      owner who signed in by phone), in their cabinet language;
    - to the business's Telegram chats linked to the platform bot, in the
      chat's language.

    A declined retry names the amount and the next retry or, after the
    last one, asks to pay or update the card; both say until when full
    service lasts. A payment that went through says thanks. Every notice
    ends with a signed link to the billing page. Each address gets one
    notice per retry however often it is queued (its outbox ids derive
    from the invoice, the attempt and the kind); one failing recipient
    never stops the others.
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
        self, business: BusinessDocument, notice: DunningNotice
    ) -> DunningRecipientCount:
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
            f"dunning:{notice.invoice_id}_{int(notice.attempt)}_{notice.kind.value}"
        )
        queued: int = 0
        for contact in self._contacts(business):
            try:
                queued += int(
                    self._manager_notifier.notify(
                        StaffNotification(
                            business_id=business.id,
                            contact=contact,
                            text=self._text(business, notice, contact.language, link),
                            subject=subject,
                        )
                    )
                )
            except Exception:
                logger.exception(
                    "A payment retry notice by %s was not queued.",
                    contact.channel.value,
                )

        return DunningRecipientCount(queued)

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

    def _text(
        self,
        business: BusinessDocument,
        notice: DunningNotice,
        language: LanguageTag,
        link: CabinetDeepLink | None,
    ) -> MessageText:
        values: dict[str, str] = {
            "business": str(business.name),
            "amount": str(format_money(notice.amount, language)),
        }
        if notice.next_retry_at is not None:
            values["next_date"] = self._date(
                notice.next_retry_at, business.timezone, language
            )

        if notice.grace_until is not None:
            values["date"] = self._date(notice.grace_until, business.timezone, language)

        lines: list[str] = [self._say(DUNNING_TEXTS[notice.kind], language, values)]
        if notice.kind is not DunningNoticeKind.PAYMENT_RECOVERED and "date" in values:
            lines[0] += self._say(FULL_SERVICE_DEADLINE, language, values)

        if link is not None:
            lines.extend(["", str(link)])

        return MessageText("\n".join(lines))

    def _date(
        self, instant: Microseconds, timezone: TimezoneName, language: LanguageTag
    ) -> str:
        return format_date(
            to_local_datetime(instant, timezone).date(),
            format=DATE_FORMAT,
            locale=require_babel_locale(language),
        )

    def _say(
        self,
        text: LocalizedText,
        language: LanguageTag,
        values: dict[str, str],
    ) -> str:
        resolved: str = str(self._resolver.resolve(text, language))
        for name, value in values.items():
            resolved = resolved.replace("{" + name + "}", value)

        return resolved
