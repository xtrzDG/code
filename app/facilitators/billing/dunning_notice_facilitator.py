from babel.dates import format_date
from typed_time_provider import Microseconds

from app.contracts.payment_methods import DunningNoticeFacilitatorContract
from app.facilitators.billing.owner_billing_notices import OwnerBillingNotices
from app.schemas.constants.payments import DunningNoticeKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.payment_retries import DunningNotice
from app.schemas.typings.billing.constrained_integers import DunningRecipientCount
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.notifications.constrained_strings import StaffAlertSubject
from app.utilities.billing.billing_periods import to_local_datetime
from app.utilities.billing.dunning_texts import DUNNING_TEXTS, FULL_SERVICE_DEADLINE
from app.utilities.localization.babel_locales import require_babel_locale
from app.utilities.money.money_formatting import format_money

DATE_FORMAT: str = "long"


class DunningNoticeFacilitator(OwnerBillingNotices, DunningNoticeFacilitatorContract):
    """
    Tells the owners how a retry of a declined automatic charge went, as
    every billing message reaches them (OwnerBillingNotices).

    A declined retry names the amount and the next retry or, after the
    last one, asks to pay or update the card; both say until when full
    service lasts. A payment that went through says thanks. Every notice
    ends with a signed link to the billing page. Each address gets one
    notice per retry however often it is queued (its outbox ids derive
    from the invoice, the attempt and the kind); one failing recipient
    never stops the others.
    """

    def send(
        self, business: BusinessDocument, notice: DunningNotice
    ) -> DunningRecipientCount:
        subject = StaffAlertSubject(
            f"dunning:{notice.invoice_id}_{int(notice.attempt)}_{notice.kind.value}"
        )
        return DunningRecipientCount(
            self.notify_owners(
                business,
                subject,
                lambda language: self._lines(business, notice, language),
                "A payment retry notice",
            )
        )

    def _lines(
        self, business: BusinessDocument, notice: DunningNotice, language: LanguageTag
    ) -> list[str]:
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

        lines: list[str] = [self.say(DUNNING_TEXTS[notice.kind], language, values)]
        if notice.kind is not DunningNoticeKind.PAYMENT_RECOVERED and "date" in values:
            lines[0] += self.say(FULL_SERVICE_DEADLINE, language, values)

        return lines

    def _date(
        self, instant: Microseconds, timezone: TimezoneName, language: LanguageTag
    ) -> str:
        return format_date(
            to_local_datetime(instant, timezone).date(),
            format=DATE_FORMAT,
            locale=require_babel_locale(language),
        )
