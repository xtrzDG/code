from typed_time_provider import Microseconds, WallClock

from app.contracts.billing import (
    PaymentGatewayAdapterContract,
    PaymentOrderRepoContract,
)
from app.contracts.repositories import InvoiceRepoContract, SubscriptionRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.billing import InvoiceKind, SubscriptionStatus
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
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.schemas.typings.billing.constrained_strings import PaymentReturnUrl
from app.schemas.typings.billing.strings import InvoiceDescription
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.billing.billing_records import (
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
from app.utilities.localization.language_tags import require_babel_locale


class StartCheckoutUseCase(UseCaseContract[StartCheckoutCommand, CheckoutSessionView]):
    """
    Owner pays the open invoices on the provider's page and subscribes the
    card to automatic charges (concept: Flitt subscriptions with auto-debit).

    Without open invoices the next service period is invoiced first: during
    the trial it starts when the trial ends (paid ahead, the trial is kept),
    otherwise at the end of the current period, or now if that has passed;
    the first monthly invoice brings the one-time setup fee. Automatic
    charges of the subscription price start on the local day the paid
    period ends. Every checkout is a new provider order, so a payment
    declined earlier can be retried.
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
        self._require_allowed_return_url(input_data.request.return_url)
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
            default=max(subscription.period_end, self._wall_clock.now_unix()),
        )
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
        open_invoices: list[InvoiceDocument] = list_open_invoices(
            list_subscription_invoices(self._invoice_repo, subscription)
        )
        if open_invoices != []:
            return open_invoices

        if (
            subscription.status is SubscriptionStatus.ACTIVE
            and subscription.provider_reference is not None
        ):
            raise ConflictError(
                "Automatic payments are already on and nothing is due now."
            )

        return self._issue_due_invoices.run(
            DueInvoicesRequest(
                business=business,
                subscription=subscription,
                period_start=max(subscription.period_end, self._wall_clock.now_unix()),
                is_setup_fee_included=True,
            )
        )

    def _require_allowed_return_url(self, return_url: PaymentReturnUrl | None) -> None:
        if return_url is None:
            return

        allowed_origins: list[str] = [
            str(origin).rstrip("/")
            for origin in self._app_settings.cors_allowed_origins
        ]
        if self._app_settings.app_base_url is not None:
            allowed_origins.append(str(self._app_settings.app_base_url).rstrip("/"))

        url: str = str(return_url)
        if not any(
            url == origin or url.startswith(f"{origin}/") for origin in allowed_origins
        ):
            raise ValidationFailedError(
                "The return page must belong to an allowed cabinet origin."
            )


def select_order_description(invoices: list[InvoiceDocument]) -> InvoiceDescription:
    """The service-period line when there is one, else the first invoice line."""

    for invoice in invoices:
        if invoice.kind is InvoiceKind.SERVICE_PERIOD:
            return invoice.description

    return invoices[0].description
