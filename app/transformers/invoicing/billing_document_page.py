"""
The parts of one invoice or receipt page, in the page's one language: the
facts under the title, the parties, the period, the tax rows and the
notes (`BillingDocumentLayoutTransformer` puts them together).
"""

from datetime import date
from decimal import Decimal

from babel import Locale
from babel.dates import format_date
from babel.numbers import format_percent
from typed_time_provider import Microseconds

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.schemas.constants.billing import InvoiceStatus
from app.schemas.constants.invoicing import TaxTreatment
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.domain.billing_profiles import InvoiceParty, PaymentCardSnapshot
from app.schemas.dto.billing import Money
from app.schemas.dto.invoicing import BillingDocumentPrintout
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.transformers.billing.billing_texts import (
    fill_placeholders,
    select_text_language,
)
from app.transformers.invoicing import billing_document_texts as texts
from app.transformers.invoicing.billing_document_sheet import SheetParty, SheetRow
from app.utilities.billing.billing_periods import to_local_datetime
from app.utilities.localization.babel_locales import require_babel_locale
from app.utilities.localization.display_names import build_country_display_name
from app.utilities.money.money_formatting import format_money

BASIS_POINTS_IN_WHOLE: Decimal = Decimal(10_000)
NO_PERIOD: str = "—"
OPEN_STATUSES: frozenset[InvoiceStatus] = frozenset(
    {InvoiceStatus.ISSUED, InvoiceStatus.FAILED}
)


class BillingDocumentPage:
    """Texts, dates and amounts of one page, all in its language."""

    def __init__(
        self,
        resolver: LocalizedTextResolverContract,
        printout: BillingDocumentPrintout,
    ) -> None:
        self._resolver: LocalizedTextResolverContract = resolver
        self._printout: BillingDocumentPrintout = printout
        self.invoice: InvoiceDocument = printout.invoice
        self.language: LanguageTag = select_text_language(
            texts.INVOICE_TITLE, printout.language
        )
        self._locale: Locale = require_babel_locale(self.language)

    def say(self, text: LocalizedText, **values: str) -> str:
        return fill_placeholders(
            str(self._resolver.resolve(text, self.language)), values
        )

    def money(self, amount_minor: MoneyAmountMinor) -> str:
        money = Money(
            amount_minor=amount_minor, currency_code=self.invoice.currency_code
        )
        return str(format_money(money, self.language))

    def day(self, instant: Microseconds) -> str:
        return self._format_day(self._local_day(instant))

    def period(self) -> str:
        """First and last local day of the period, the last one inclusive."""

        if self.invoice.period_end <= self.invoice.period_start:
            return NO_PERIOD

        first_day: date = self._local_day(self.invoice.period_start)
        last_day: date = max(
            self._local_day(Microseconds(int(self.invoice.period_end) - 1)), first_day
        )
        return f"{self._format_day(first_day)} – {self._format_day(last_day)}"

    def rate(self) -> str:
        basis_points: int = int(self.invoice.tax_rate_basis_points or 0)
        return format_percent(
            Decimal(basis_points) / BASIS_POINTS_IN_WHOLE,
            locale=self._locale,
            decimal_quantization=False,
        )

    def subtotal_minor(self) -> MoneyAmountMinor:
        return self.invoice.subtotal_minor or self.invoice.amount_minor

    def tax_rows(self) -> list[SheetRow]:
        """Subtotal and VAT, when VAT is charged."""

        if not self.invoice.tax_minor:
            return []

        return [
            SheetRow(self.say(texts.SUBTOTAL), self.money(self.subtotal_minor())),
            SheetRow(
                self.say(texts.VAT, rate=self.rate()),
                self.money(self.invoice.tax_minor),
            ),
        ]

    def facts(self, is_receipt: bool) -> list[SheetRow]:
        paid_at: Microseconds | None = self.invoice.paid_at
        rows: list[SheetRow] = []
        if not is_receipt:
            rows.append(
                SheetRow(self.say(texts.ISSUE_DATE), self.day(self.invoice.created_at))
            )

        if paid_at is not None and self.invoice.status is InvoiceStatus.PAID:
            rows.append(SheetRow(self.say(texts.PAYMENT_DATE), self.day(paid_at)))
            rows.append(SheetRow(self.say(texts.PAYMENT_METHOD), self.card()))

        return rows

    def card(self) -> str:
        card: PaymentCardSnapshot | None = self.invoice.payment_card
        if card is None or card.last_digits is None:
            return self.say(texts.CARD_UNKNOWN)

        if card.brand is None:
            return self.say(texts.CARD_WITHOUT_BRAND, digits=str(card.last_digits))

        return self.say(
            texts.CARD_WITH_BRAND,
            brand=str(card.brand),
            digits=str(card.last_digits),
        )

    def party(self, heading: LocalizedText, party: InvoiceParty) -> SheetParty:
        lines: list[str] = []
        if party.address is not None:
            lines.append(str(party.address))

        lines.append(str(build_country_display_name(party.country_code, self._locale)))
        if party.tax_id is not None:
            lines.append(f"{self.say(texts.TAX_ID)}: {party.tax_id}")

        if party.email is not None:
            lines.append(f"{self.say(texts.EMAIL)}: {party.email}")

        return SheetParty(self.say(heading), str(party.legal_name), lines)

    def grand_total_label(self, is_receipt: bool) -> LocalizedText:
        if is_receipt:
            return texts.AMOUNT_RECEIVED

        if self.invoice.status is InvoiceStatus.PAID:
            return texts.TOTAL_PAID

        return texts.TOTAL_DUE

    def notes(self, is_receipt: bool) -> list[str]:
        notes: list[str] = []
        if is_receipt:
            notes.append(self.say(texts.RECEIPT_THANKS))
        elif self.invoice.status in OPEN_STATUSES:
            notes.append(self.say(texts.PAY_ONLINE))

        notes.append(self.tax_note())
        return notes

    def tax_note(self) -> str:
        treatment: TaxTreatment = (
            self.invoice.tax_treatment or TaxTreatment.NOT_REGISTERED
        )
        seller: InvoiceParty | None = self.invoice.seller
        country: str = (
            ""
            if seller is None
            else str(build_country_display_name(seller.country_code, self._locale))
        )
        return self.say(texts.TAX_NOTES[treatment], rate=self.rate(), country=country)

    def _local_day(self, instant: Microseconds) -> date:
        return to_local_datetime(instant, self._printout.timezone).date()

    def _format_day(self, day: date) -> str:
        return format_date(day, format="medium", locale=self._locale)
