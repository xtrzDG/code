from typed_time_provider import Microseconds, WallClock

from app.contracts.billing_credits import BillingCreditLockRegistryContract
from app.contracts.invoicing import InvoiceIssuingFacilitatorContract
from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories.billing_repositories import InvoiceRepoContract
from app.contracts.repositories.client_care_repositories import (
    BillingCreditRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import (
    BillingPeriod,
    InvoiceKind,
    InvoiceStatus,
    SetupOption,
)
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.billing_profiles import InvoiceLineText
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.billing import Money, PlanDefinition
from app.schemas.dto.billing_ledger import DueInvoicesRequest, InvoiceDescriptionInput
from app.schemas.typings.billing.strings import InvoiceDescription
from app.use_cases.billing.invoice_issuing_adjustments import (
    InvoiceIssuingAdjustments,
    settled_status,
)
from app.use_cases.billing.invoice_period_terms import (
    describe_line,
    period_end,
    period_price,
)
from app.use_cases.shared.billing_records import OPEN_INVOICE_STATUSES
from app.use_cases.shared.invoice_payments import record_invoice_payment
from app.use_cases.shared.subscription_pricing import price_setup_fee


class IssueDueInvoicesUseCase(
    UseCaseContract[DueInvoicesRequest, list[InvoiceDocument]]
):
    """
    Issue the invoice of a service period at its start, in the subscription
    currency and at the subscription price, with the localized service
    wording (concept tax rule: never "license" or "consultation").

    The one-time setup fee is invoiced together with the first monthly
    period, and only for a business set up by the platform team
    (DONE_FOR_YOU): an owner who set the assistant up in the cabinet
    (SELF_SERVE, or a subscription from before the choice existed) pays no
    setup fee. An annual subscription includes it (concept: the setup fee
    is credited to an annual payment), so a business that has already paid
    any service period (an annual one included) never gets it again, for
    example after switching from annual to monthly. Issuing is idempotent:
    an existing invoice of the same period is reused, and an open one takes
    the requested PAID or FAILED status. A new invoice is numbered, names
    the seller and the buyer, and carries the VAT of the tax policy on top
    of the price (`InvoiceIssuingFacilitator`); a paid one records when
    and with which card.

    What the platform team granted (R13) comes off the price before tax of
    an invoice issued to be paid: the client's discount on its service
    periods, then its credit (`InvoiceIssuingAdjustments`); a setup fee the
    team waived is never invoiced. An invoice that leaves nothing to pay is
    paid at once. A period the provider has already charged totals exactly
    the charge, so neither applies to it.

    A month of a seasonal pause (R14, `pause_price_percent`) is invoiced
    like a period, at its share of the monthly price and worded as a
    pause, and never brings the setup fee (`invoice_period_terms.py`).
    """

    def __init__(
        self,
        invoice_repo: InvoiceRepoContract,
        plan_registry: PlanRegistryContract,
        invoice_description_transformer: TransformerContract[
            InvoiceDescriptionInput,
            InvoiceDescription,
        ],
        wall_clock: WallClock[Microseconds],
        invoice_issuing: InvoiceIssuingFacilitatorContract,
        invoice_line_texts_transformer: TransformerContract[
            InvoiceDescriptionInput,
            list[InvoiceLineText],
        ],
        billing_credit_repo: BillingCreditRepoContract,
        credit_lock: BillingCreditLockRegistryContract,
    ) -> None:
        self._adjustments: InvoiceIssuingAdjustments = InvoiceIssuingAdjustments(
            invoice_repo, billing_credit_repo, credit_lock
        )
        self._invoice_issuing: InvoiceIssuingFacilitatorContract = invoice_issuing
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._plan_registry: PlanRegistryContract = plan_registry
        self._invoice_description_transformer: TransformerContract[
            InvoiceDescriptionInput,
            InvoiceDescription,
        ] = invoice_description_transformer
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._invoice_line_texts_transformer: TransformerContract[
            InvoiceDescriptionInput,
            list[InvoiceLineText],
        ] = invoice_line_texts_transformer

    def run(self, input_data: DueInvoicesRequest) -> list[InvoiceDocument]:
        business: BusinessDocument = input_data.business
        subscription: SubscriptionDocument = input_data.subscription
        plan: PlanDefinition = self._plan_registry.get(subscription.plan_key)
        business_invoices: list[InvoiceDocument] = self._invoice_repo.list_by_business(
            business.id
        )
        issued: list[InvoiceDocument] = []
        if self._needs_setup_fee(input_data, business_invoices):
            issued.append(self._issue_setup_fee(input_data, plan))

        issued.append(self._issue_period_invoice(input_data, plan, business_invoices))
        return issued

    def _needs_setup_fee(
        self,
        input_data: DueInvoicesRequest,
        business_invoices: list[InvoiceDocument],
    ) -> bool:
        if (
            not input_data.is_setup_fee_included
            or input_data.pause_price_percent is not None
            or input_data.subscription.billing_period is not BillingPeriod.MONTHLY
            or input_data.subscription.setup_option is not SetupOption.DONE_FOR_YOU
            or input_data.subscription.is_setup_fee_waived
        ):
            return False

        return not any(
            (
                invoice.kind is InvoiceKind.SETUP_FEE
                and invoice.status is not InvoiceStatus.VOID
            )
            or (
                invoice.kind is InvoiceKind.SERVICE_PERIOD
                and invoice.status is InvoiceStatus.PAID
            )
            for invoice in business_invoices
        )

    def _issue_setup_fee(
        self,
        input_data: DueInvoicesRequest,
        plan: PlanDefinition,
    ) -> InvoiceDocument:
        subscription: SubscriptionDocument = input_data.subscription
        now: Microseconds = self._wall_clock.now_unix()
        setup_fee: Money = price_setup_fee(
            self._plan_registry,
            subscription.plan_key,
            subscription.currency_code,
            SetupOption.DONE_FOR_YOU,
        )
        line: InvoiceDescriptionInput = describe_line(
            input_data, plan, InvoiceKind.SETUP_FEE, now, now
        )
        invoice = InvoiceDocument(
            business_id=subscription.business_id,
            subscription_id=subscription.id,
            kind=InvoiceKind.SETUP_FEE,
            description=self._invoice_description_transformer.transform(line),
            line_texts=self._invoice_line_texts_transformer.transform(line),
            amount_minor=setup_fee.amount_minor,
            currency_code=setup_fee.currency_code,
            period_start=now,
            period_end=now,
            provider_reference=input_data.payment_reference,
            created_at=now,
            updated_at=now,
        )
        return self._save_issued(input_data, invoice, now)

    def _issue_period_invoice(
        self,
        input_data: DueInvoicesRequest,
        plan: PlanDefinition,
        business_invoices: list[InvoiceDocument],
    ) -> InvoiceDocument:
        subscription: SubscriptionDocument = input_data.subscription
        now: Microseconds = self._wall_clock.now_unix()
        for invoice in business_invoices:
            if (
                invoice.subscription_id == subscription.id
                and invoice.kind is InvoiceKind.SERVICE_PERIOD
                and invoice.status is not InvoiceStatus.VOID
                and invoice.period_start == input_data.period_start
            ):
                return self._settle_existing(invoice, input_data, now)

        end: Microseconds = period_end(input_data)
        line: InvoiceDescriptionInput = describe_line(
            input_data, plan, InvoiceKind.SERVICE_PERIOD, input_data.period_start, end
        )
        draft = InvoiceDocument(
            business_id=subscription.business_id,
            subscription_id=subscription.id,
            kind=InvoiceKind.SERVICE_PERIOD,
            description=self._invoice_description_transformer.transform(line),
            line_texts=self._invoice_line_texts_transformer.transform(line),
            amount_minor=period_price(input_data),
            currency_code=subscription.currency_code,
            period_start=input_data.period_start,
            period_end=end,
            provider_reference=input_data.payment_reference,
            created_at=now,
            updated_at=now,
        )
        return self._save_issued(input_data, draft, now)

    def _save_issued(
        self,
        input_data: DueInvoicesRequest,
        draft: InvoiceDocument,
        now: Microseconds,
    ) -> InvoiceDocument:
        """
        Discount and credit off the price of a bill to pay, then number,
        parties and VAT, the requested status (paid when nothing is left to
        pay), and stored.
        """

        charged: Money | None = (
            input_data.charged_amount
            if draft.kind is InvoiceKind.SERVICE_PERIOD
            else None
        )

        def issue_and_store(adjusted: InvoiceDocument) -> InvoiceDocument:
            invoice: InvoiceDocument = self._invoice_issuing.issue(
                input_data.business, adjusted, charged=charged
            )
            record_invoice_payment(
                invoice,
                settled_status(input_data.status, invoice),
                input_data.payment_card,
                now,
            )
            self._invoice_repo.save(invoice)
            return invoice

        if charged is not None:
            return issue_and_store(draft)

        return self._adjustments.issue(
            input_data.subscription, draft, issue_and_store, now
        )

    def _settle_existing(
        self,
        invoice: InvoiceDocument,
        input_data: DueInvoicesRequest,
        now: Microseconds,
    ) -> InvoiceDocument:
        if (
            input_data.status is InvoiceStatus.ISSUED
            or invoice.status not in OPEN_INVOICE_STATUSES
        ):
            return invoice

        record_invoice_payment(invoice, input_data.status, input_data.payment_card, now)
        if input_data.payment_reference is not None:
            invoice.provider_reference = input_data.payment_reference

        invoice.updated_at = now
        self._invoice_repo.save(invoice)
        return invoice
