from typed_time_provider import Microseconds, WallClock

from app.contracts.invoicing import InvoiceIssuingFacilitatorContract
from app.contracts.payment_methods import (
    PaymentProviderRegistryContract,
    PaymentRetryRepoContract,
)
from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
)
from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.payment_methods import (
    PaymentMethodQuery,
    PaymentMethodView,
    PaymentRetryView,
)
from app.use_cases.billing.card_on_file.card_on_file_views import (
    build_card_view,
    can_save_card,
    is_trial_card_prompt_due,
    select_card_provider,
)
from app.use_cases.billing.card_on_file.card_setup_terms import quote_setup_fee_due
from app.use_cases.billing.card_on_file.dunning_rules import (
    build_retry_view,
    find_dunning_invoice,
    find_grace_start_of,
)
from app.use_cases.shared.billing_records import (
    find_current_subscription,
    list_subscription_invoices,
)


class GetPaymentMethodUseCase(UseCaseContract[PaymentMethodQuery, PaymentMethodView]):
    """
    The card on file of a business (GET .../billing/payment-method, owners
    only): the card the automatic charges go to (brand, last digits,
    expiry), who charges it, whether a card may be saved or replaced now
    (and the trial's setup fee saving it charges), the trial's "Save card"
    prompt from day 10, and where the retries of a declined charge stand.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
        payment_retry_repo: PaymentRetryRepoContract,
        plan_registry: PlanRegistryContract,
        payment_provider_registry: PaymentProviderRegistryContract,
        wall_clock: WallClock[Microseconds],
        invoice_issuing: InvoiceIssuingFacilitatorContract,
        brand_repo: BrandRepoContract,
        business_repo: BusinessRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._payment_retry_repo: PaymentRetryRepoContract = payment_retry_repo
        self._plan_registry: PlanRegistryContract = plan_registry
        self._payment_provider_registry: PaymentProviderRegistryContract = (
            payment_provider_registry
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._invoice_issuing: InvoiceIssuingFacilitatorContract = invoice_issuing
        self._brand_repo: BrandRepoContract = brand_repo
        self._business_repo: BusinessRepoContract = business_repo

    def run(self, input_data: PaymentMethodQuery) -> PaymentMethodView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        subscription: SubscriptionDocument | None = find_current_subscription(
            self._subscription_repo, business.id
        )
        invoices: list[InvoiceDocument] = (
            []
            if subscription is None
            else list_subscription_invoices(self._invoice_repo, subscription)
        )
        now: Microseconds = self._wall_clock.now_unix()
        can_save: bool = can_save_card(subscription, invoices)
        return PaymentMethodView(
            provider=select_card_provider(
                self._payment_provider_registry, business, subscription
            ),
            card=build_card_view(
                None if subscription is None else subscription.payment_method_summary
            ),
            has_auto_debit=(
                subscription is not None and subscription.provider_reference is not None
            ),
            can_save_card=can_save,
            trial_ends_at=None if subscription is None else subscription.trial_ends_at,
            is_trial_card_prompt_due=is_trial_card_prompt_due(
                subscription, business, now
            ),
            retry=self._retry_view(business, subscription, invoices),
            setup_fee_due=(
                quote_setup_fee_due(
                    self._plan_registry,
                    self._invoice_issuing,
                    self._brand_repo,
                    self._business_repo,
                    business,
                    subscription,
                    self._invoice_repo.list_by_business(business.id),
                )
                if can_save
                else None
            ),
        )

    def _retry_view(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument | None,
        invoices: list[InvoiceDocument],
    ) -> PaymentRetryView | None:
        if subscription is None:
            return None

        invoice: InvoiceDocument | None = find_dunning_invoice(subscription, invoices)
        grace_start = find_grace_start_of(self._plan_registry, subscription, business)
        if invoice is None or grace_start is None:
            return None

        return build_retry_view(
            self._payment_retry_repo, invoice, subscription, business, grace_start
        )
