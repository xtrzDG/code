from typed_time_provider import Microseconds, WallClock

from app.contracts.billing import (
    PaymentGatewayAdapterContract,
    PaymentOrderRepoContract,
)
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.billing import (
    InvoiceKind,
    InvoiceStatus,
    SubscriptionStatus,
)
from app.schemas.constants.payments import PaymentProvider
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.billing import Money
from app.schemas.dto.billing_cabinet import (
    CheckoutSessionView,
    StartCheckoutCommand,
)
from app.schemas.dto.billing_ledger import DueInvoicesRequest
from app.schemas.dto.payments import (
    PaymentCheckoutRequest,
    PaymentCheckoutSession,
    RecurringCharge,
)
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.billing.prefixed_id import InvoiceId
from app.schemas.typings.billing.strings import InvoiceDescription
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.billing.billing_records import (
    OPEN_INVOICE_STATUSES,
    find_covering_paid_invoice,
    find_next_period_start,
    list_open_invoices,
    list_subscription_invoices,
    require_current_subscription,
    sum_invoice_amounts,
)
from app.use_cases.billing.subscription_pricing import quote_money
from app.utilities.billing.billing_periods import (
    get_interval_months,
    to_local_calendar_day,
)
from app.utilities.billing.return_urls import require_allowed_return_url
from app.utilities.localization.language_tags import require_babel_locale


class StartCheckoutUseCase(UseCaseContract[StartCheckoutCommand, CheckoutSessionView]):
    """
    Owner pays the open invoices on the provider's page and subscribes the
    card to automatic charges (concept: Flitt subscriptions with auto-debit).

    Without open invoices the next service period is invoiced first: during
    the trial it starts when the trial ends (paid ahead, the trial is kept),
    otherwise at the end of the current period or of a period already paid
    ahead, or now if that has passed; the first monthly invoice brings the
    one-time setup fee. A bill that is already paid is never collected
    again, and while automatic charges run (in the trial too) there is
    nothing to pay. An unpaid period that has already ended is voided and
    a fresh period starting now is billed instead, so a late payment buys
    service from today. Automatic charges of the subscription price start
    on the local day the paid period ends, never in the past. Every
    checkout is a new provider order, so a payment declined earlier can be
    retried.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
        payment_order_repo: PaymentOrderRepoContract,
        issue_due_invoices: UseCaseContract[DueInvoicesRequest, list[InvoiceDocument]],
        payment_gateway: PaymentGatewayAdapterContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._payment_order_repo: PaymentOrderRepoContract = payment_order_repo
        self._issue_due_invoices: UseCaseContract[
            DueInvoicesRequest,
            list[InvoiceDocument],
        ] = issue_due_invoices
        self._payment_gateway: PaymentGatewayAdapterContract = payment_gateway
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: StartCheckoutCommand) -> CheckoutSessionView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        language: LanguageTag = input_data.display_language or business.owner_language
        require_babel_locale(language)
        require_allowed_return_url(input_data.request.return_url, self._app_settings)
        subscription: SubscriptionDocument = require_current_subscription(
            self._subscription_repo,
            business.id,
        )
        invoices: list[InvoiceDocument] = self._collect_invoices_to_pay(
            business,
            subscription,
        )
        amount: Money = sum_invoice_amounts(invoices)
        if amount.currency_code != subscription.currency_code:
            raise ConflictError("Open invoices are not in the subscription currency.")

        paid_until: Microseconds = max(
            [
                invoice.period_end
                for invoice in invoices
                if invoice.kind is InvoiceKind.SERVICE_PERIOD
            ],
            default=find_next_period_start(
                subscription,
                list_subscription_invoices(self._invoice_repo, subscription),
            ),
        )
        paid_until = max(paid_until, self._wall_clock.now_unix())
        payment_order = PaymentOrderDocument(
            business_id=business.id,
            subscription_id=subscription.id,
            provider=PaymentProvider.FLITT,
            invoice_ids=[invoice.id for invoice in invoices],
            amount_minor=amount.amount_minor,
            currency_code=amount.currency_code,
            recurring_amount_minor=subscription.price_minor,
            recurring_interval_months=get_interval_months(subscription.billing_period),
        )
        session: PaymentCheckoutSession = self._payment_gateway.create_checkout(
            PaymentCheckoutRequest(
                payment_order_id=payment_order.id,
                amount=amount,
                description=select_order_description(invoices),
                recurring_charge=RecurringCharge(
                    amount=Money(
                        amount_minor=subscription.price_minor,
                        currency_code=subscription.currency_code,
                    ),
                    interval_months=payment_order.recurring_interval_months,
                    start_date=to_local_calendar_day(paid_until, business.timezone),
                ),
                language=language,
                return_url=input_data.request.return_url,
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        payment_order.checkout_url = session.checkout_url
        payment_order.last_payment_reference = session.payment_reference
        payment_order.created_at = now
        payment_order.updated_at = now
        self._payment_order_repo.save(payment_order)
        return CheckoutSessionView(
            payment_order_id=payment_order.id,
            checkout_url=session.checkout_url,
            amount=quote_money(amount, False, language),
            invoice_ids=list(payment_order.invoice_ids),
        )

    def _collect_invoices_to_pay(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
    ) -> list[InvoiceDocument]:
        now: Microseconds = self._wall_clock.now_unix()
        invoices: list[InvoiceDocument] = list_subscription_invoices(
            self._invoice_repo,
            subscription,
        )
        open_invoices: list[InvoiceDocument] = list_open_invoices(invoices)
        ended_periods: list[InvoiceDocument] = [
            invoice
            for invoice in open_invoices
            if invoice.kind is InvoiceKind.SERVICE_PERIOD and invoice.period_end <= now
        ]
        if ended_periods != []:
            return self._rebill_from_now(
                business,
                subscription,
                open_invoices,
                ended_periods,
                now,
            )

        if open_invoices != []:
            if self._is_service_unpaid(subscription, invoices, open_invoices, now):
                open_ids: set[InvoiceId] = {invoice.id for invoice in open_invoices}
                return open_invoices + [
                    invoice
                    for invoice in self._issue_payable(
                        business,
                        subscription,
                        max(find_next_period_start(subscription, invoices), now),
                    )
                    if invoice.id not in open_ids
                ]

            return open_invoices

        if subscription.provider_reference is not None:
            raise ConflictError(
                "Automatic payments are already on and nothing is due now."
            )

        return self._issue_payable(
            business,
            subscription,
            max(find_next_period_start(subscription, invoices), now),
        )

    def _is_service_unpaid(
        self,
        subscription: SubscriptionDocument,
        invoices: list[InvoiceDocument],
        open_invoices: list[InvoiceDocument],
        now: Microseconds,
    ) -> bool:
        """
        Only other bills (e.g. minutes above the package) are open while the
        subscription is not active and no paid period or running trial
        covers now: the service itself must be paid too, or paying would
        not restore it. An active subscription is renewed by its automatic
        charges instead.
        """

        is_trial_running: bool = (
            subscription.trial_ends_at is not None and now < subscription.trial_ends_at
        )
        return (
            subscription.status is not SubscriptionStatus.ACTIVE
            and not is_trial_running
            and find_covering_paid_invoice(invoices, now) is None
            and all(
                invoice.kind is not InvoiceKind.SERVICE_PERIOD
                for invoice in open_invoices
            )
        )

    def _rebill_from_now(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
        open_invoices: list[InvoiceDocument],
        ended_periods: list[InvoiceDocument],
        now: Microseconds,
    ) -> list[InvoiceDocument]:
        """
        Void unpaid periods that are already over and bill a fresh period
        from now, keeping the other open bills (setup fee, overage).
        """

        for invoice in ended_periods:
            invoice.status = InvoiceStatus.VOID
            invoice.updated_at = now
            self._invoice_repo.save(invoice)

        voided_ids: set[InvoiceId] = {invoice.id for invoice in ended_periods}
        kept: list[InvoiceDocument] = [
            invoice for invoice in open_invoices if invoice.id not in voided_ids
        ]
        kept_ids: set[InvoiceId] = {invoice.id for invoice in kept}
        fresh: list[InvoiceDocument] = self._issue_payable(business, subscription, now)
        return kept + [invoice for invoice in fresh if invoice.id not in kept_ids]

    def _issue_payable(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
        period_start: Microseconds,
    ) -> list[InvoiceDocument]:
        """
        Bills of the period starting then; a period already paid is never
        collected again.

        Raises:
            ConflictError: the period is already paid.
        """

        payable: list[InvoiceDocument] = [
            invoice
            for invoice in self._issue_due_invoices.run(
                DueInvoicesRequest(
                    business=business,
                    subscription=subscription,
                    period_start=period_start,
                    is_setup_fee_included=True,
                )
            )
            if invoice.status in OPEN_INVOICE_STATUSES
        ]
        if payable == []:
            raise ConflictError("There is nothing to pay.")

        return payable


def select_order_description(invoices: list[InvoiceDocument]) -> InvoiceDescription:
    """The service-period line when there is one, else the first invoice line."""

    for invoice in invoices:
        if invoice.kind is InvoiceKind.SERVICE_PERIOD:
            return invoice.description

    return invoices[0].description
