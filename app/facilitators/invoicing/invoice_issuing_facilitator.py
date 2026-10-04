from typed_time_provider import Microseconds, WallClock

from app.contracts.invoicing import (
    BillingProfileRepoContract,
    InvoiceCounterRepoContract,
    InvoiceIssuingFacilitatorContract,
    TaxPolicyRegistryContract,
)
from app.schemas.configurations.seller_settings import SellerSettings
from app.schemas.constants.invoicing import TaxTreatment
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.domain.billing_profiles import InvoiceParty
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.billing import Money
from app.schemas.dto.invoicing import TaxDecision, TaxedAmount
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.invoicing.constrained_integers import (
    InvoiceSequenceNumber,
    InvoiceYear,
    TaxRateBasisPoints,
)
from app.schemas.typings.invoicing.constrained_strings import InvoiceNumber
from app.utilities.billing.billing_periods import to_local_datetime
from app.utilities.billing.invoice_parties import (
    build_buyer_party,
    build_seller_party,
    build_tax_buyer,
)
from app.utilities.billing.invoicing_keys import build_invoice_number
from app.utilities.billing.tax_math import add_tax, extract_tax

NO_TAX: TaxRateBasisPoints = TaxRateBasisPoints(0)


class InvoiceIssuingFacilitator(InvoiceIssuingFacilitatorContract):
    """
    Makes an invoice the accountant's invoice when it is issued: the next
    number of the seller's series in the year of its issue (in the seller's
    time zone), the seller (SELLER_*) and the buyer (the business's billing
    details, else its name and country) copied as they are now, and the
    VAT the tax policy decides for that buyer added on top of the price.
    """

    def __init__(
        self,
        billing_profile_repo: BillingProfileRepoContract,
        invoice_counter_repo: InvoiceCounterRepoContract,
        tax_policy_registry: TaxPolicyRegistryContract,
        seller: SellerSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._billing_profile_repo: BillingProfileRepoContract = billing_profile_repo
        self._invoice_counter_repo: InvoiceCounterRepoContract = invoice_counter_repo
        self._tax_policy_registry: TaxPolicyRegistryContract = tax_policy_registry
        self._seller: SellerSettings = seller

    def price_with_tax(self, business: BusinessDocument, net: Money) -> TaxedAmount:
        return add_tax(net, self._decide(self._buyer(business)))

    def issue(
        self,
        business: BusinessDocument,
        invoice: InvoiceDocument,
        *,
        charged: Money | None = None,
    ) -> InvoiceDocument:
        if invoice.number is not None:
            return invoice

        buyer: InvoiceParty = self._buyer(business)
        decision: TaxDecision = self._decide(buyer)
        taxed: TaxedAmount = (
            add_tax(
                Money(
                    amount_minor=invoice.amount_minor,
                    currency_code=invoice.currency_code,
                ),
                decision,
            )
            if charged is None or charged.currency_code != invoice.currency_code
            else extract_tax(charged, decision)
        )
        return invoice.model_copy(
            update={
                "number": self._take_number(invoice),
                "seller": build_seller_party(self._seller),
                "buyer": buyer,
                "subtotal_minor": taxed.subtotal.amount_minor,
                "tax_rate_basis_points": taxed.decision.rate_basis_points,
                "tax_minor": taxed.tax.amount_minor,
                "tax_treatment": taxed.decision.treatment,
                "amount_minor": taxed.total.amount_minor,
            }
        )

    def complete(
        self, business: BusinessDocument, invoice: InvoiceDocument
    ) -> InvoiceDocument:
        if invoice.number is not None:
            return invoice

        return invoice.model_copy(
            update={
                "number": self._take_number(invoice),
                "seller": build_seller_party(self._seller),
                "buyer": self._buyer(business),
                "subtotal_minor": invoice.amount_minor,
                "tax_rate_basis_points": NO_TAX,
                "tax_minor": MoneyAmountMinor(0),
                "tax_treatment": TaxTreatment.NOT_REGISTERED,
            }
        )

    def _buyer(self, business: BusinessDocument) -> InvoiceParty:
        return build_buyer_party(
            business, self._billing_profile_repo.get_by_business(business.id)
        )

    def _decide(self, buyer: InvoiceParty) -> TaxDecision:
        return self._tax_policy_registry.decide(build_tax_buyer(buyer))

    def _take_number(self, invoice: InvoiceDocument) -> InvoiceNumber:
        year = InvoiceYear(
            to_local_datetime(invoice.created_at, self._seller.time_zone).year
        )
        sequence: InvoiceSequenceNumber = self._invoice_counter_repo.take_next(
            self._seller.invoice_series, year, self._wall_clock.now_unix()
        )
        return build_invoice_number(self._seller.invoice_series, year, sequence)
