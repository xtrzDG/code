"""The bill and the usage line of one rental month, each written once."""

from typed_time_provider import Microseconds

from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.contracts.invoicing import InvoiceIssuingFacilitatorContract
from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    UsageEventRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.billing import InvoiceKind, InvoiceStatus, UsageKind
from app.schemas.domain.billing import (
    InvoiceDocument,
    SubscriptionDocument,
    UsageEventDocument,
)
from app.schemas.domain.billing_profiles import InvoiceLineText
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.phone_numbers import PhoneNumberDocument
from app.schemas.dto.billing import Money, PlanDefinition
from app.schemas.dto.billing_ledger import InvoiceDescriptionInput
from app.schemas.dto.catalog.plan_quotes import ExchangeRateQuote
from app.schemas.typings.billing.constrained_integers import (
    MoneyAmountMinor,
    UsageQuantity,
)
from app.schemas.typings.billing.strings import InvoiceDescription
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.localization.strings import FormattedPhoneNumber
from app.utilities.money.money_math import convert_money

ONE_MONTH: UsageQuantity = UsageQuantity(1)


class RentalBills:
    """
    Writes a rental month's invoice (NUMBER_RENTAL, on the subscription, in
    its currency) and usage event (the carrier's monthly price as the
    cost), each only when it is not there yet, so a run that stopped
    halfway writes nothing twice when it is run again.
    """

    def __init__(
        self,
        invoice_repo: InvoiceRepoContract,
        usage_event_repo: UsageEventRepoContract,
        plan_registry: PlanRegistryContract,
        exchange_rate_registry: ExchangeRateRegistryContract,
        invoice_issuing: InvoiceIssuingFacilitatorContract,
        invoice_description_transformer: TransformerContract[
            InvoiceDescriptionInput, InvoiceDescription
        ],
        invoice_line_texts_transformer: TransformerContract[
            InvoiceDescriptionInput, list[InvoiceLineText]
        ],
    ) -> None:
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._usage_event_repo: UsageEventRepoContract = usage_event_repo
        self._plan_registry: PlanRegistryContract = plan_registry
        self._exchange_rate_registry: ExchangeRateRegistryContract = (
            exchange_rate_registry
        )
        self._invoice_issuing: InvoiceIssuingFacilitatorContract = invoice_issuing
        self._describe: TransformerContract[
            InvoiceDescriptionInput, InvoiceDescription
        ] = invoice_description_transformer
        self._word_lines: TransformerContract[
            InvoiceDescriptionInput, list[InvoiceLineText]
        ] = invoice_line_texts_transformer

    def price_in(
        self, number: PhoneNumberDocument, currency_code: CurrencyCode
    ) -> Money | None:
        """
        The month's price in the subscription's currency: as fixed when the
        number was taken, else converted at today's official rate; None
        when no bank publishes one (the month is billed on a later run).
        """

        price = Money(
            amount_minor=MoneyAmountMinor(int(number.monthly_price_minor)),
            currency_code=number.currency_code,
        )
        if price.currency_code == currency_code:
            return price

        rate: ExchangeRateQuote | None = self._exchange_rate_registry.find_rate(
            price.currency_code, currency_code
        )
        if rate is None:
            return None

        return convert_money(price, rate.rate_value, currency_code)

    def issue_invoice(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
        display_number: FormattedPhoneNumber,
        price: Money,
        month: tuple[Microseconds, Microseconds],
        now: Microseconds,
    ) -> InvoiceDocument | None:
        """The month's bill, issued now; None when it was issued before."""

        start, end = month
        if any(
            invoice.kind is InvoiceKind.NUMBER_RENTAL
            and invoice.period_start == start
            and invoice.status is not InvoiceStatus.VOID
            for invoice in self._invoice_repo.list_by_business(business.id)
        ):
            return None

        plan: PlanDefinition = self._plan_registry.get(subscription.plan_key)
        line = InvoiceDescriptionInput(
            kind=InvoiceKind.NUMBER_RENTAL,
            language=business.owner_language,
            timezone=business.timezone,
            plan_names=plan.names,
            billing_period=subscription.billing_period,
            period_start=start,
            period_end=end,
            rented_phone_number=display_number,
        )
        draft = InvoiceDocument(
            business_id=business.id,
            subscription_id=subscription.id,
            kind=InvoiceKind.NUMBER_RENTAL,
            description=self._describe.transform(line),
            line_texts=self._word_lines.transform(line),
            amount_minor=price.amount_minor,
            currency_code=price.currency_code,
            status=InvoiceStatus.ISSUED,
            period_start=start,
            period_end=end,
            created_at=now,
            updated_at=now,
        )
        invoice: InvoiceDocument = self._invoice_issuing.issue(business, draft)
        self._invoice_repo.save(invoice)
        return invoice

    def record_usage(
        self, number: PhoneNumberDocument, month_start: Microseconds, now: Microseconds
    ) -> None:
        """The month as usage with the carrier's cost, unless recorded before."""

        if any(
            event.kind is UsageKind.NUMBER_RENTAL
            for event in self._usage_event_repo.list_by_business_between(
                number.business_id,
                month_start,
                Microseconds(int(month_start) + 1),
            )
        ):
            return

        self._usage_event_repo.append(
            UsageEventDocument(
                business_id=number.business_id,
                kind=UsageKind.NUMBER_RENTAL,
                quantity=ONE_MONTH,
                cost_micro_usd=number.monthly_cost_micro_usd,
                occurred_at=month_start,
                created_at=now,
                updated_at=now,
            )
        )
