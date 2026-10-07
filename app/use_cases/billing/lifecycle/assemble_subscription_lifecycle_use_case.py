from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
)
from app.contracts.repositories.client_care_repositories import (
    BillingCreditRepoContract,
)
from app.contracts.repositories.subscription_event_repositories import (
    SubscriptionEventRepoContract,
)
from app.contracts.subscription_lifecycle import (
    SubscriptionLifecyclePolicyRegistryContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.subscription_lifecycle import (
    CancellationReason,
    RetentionOfferKind,
)
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.billing_cabinet import BillingOverviewSource
from app.schemas.dto.subscription_lifecycle import (
    CancellationOfferView,
    PauseAvailability,
    SubscriptionLifecycleView,
)
from app.schemas.dto.subscription_lifecycle_policy import SubscriptionLifecyclePolicy
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.billing.lifecycle.lifecycle_views import view_offer, view_pause
from app.use_cases.billing.lifecycle.pause_availability import (
    read_pause_availability,
)
from app.use_cases.billing.lifecycle.retention_offers import (
    OfferInputs,
    gather_offer_inputs,
    offer_for,
)
from app.use_cases.shared.billing_records import (
    find_current_subscription,
    list_subscription_invoices,
)


class AssembleSubscriptionLifecycleUseCase(
    UseCaseContract[BillingOverviewSource, SubscriptionLifecycleView]
):
    """
    The cancel dialog and the pause card of an already authorized business:
    for every cancellation reason, in the order the dialog lists them, the
    offer the business can take instead (or none), and whether, from when,
    for how long and at what price a seasonal pause is possible.
    """

    def __init__(
        self,
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
        subscription_event_repo: SubscriptionEventRepoContract,
        billing_credit_repo: BillingCreditRepoContract,
        plan_registry: PlanRegistryContract,
        lifecycle_policy_registry: SubscriptionLifecyclePolicyRegistryContract,
        localized_text_resolver: LocalizedTextResolverContract,
        app_settings: AppSettings,
    ) -> None:
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._subscription_event_repo: SubscriptionEventRepoContract = (
            subscription_event_repo
        )
        self._billing_credit_repo: BillingCreditRepoContract = billing_credit_repo
        self._plan_registry: PlanRegistryContract = plan_registry
        self._lifecycle_policy_registry: SubscriptionLifecyclePolicyRegistryContract = (
            lifecycle_policy_registry
        )
        self._localized_text_resolver: LocalizedTextResolverContract = (
            localized_text_resolver
        )
        self._app_settings: AppSettings = app_settings

    def run(self, input_data: BillingOverviewSource) -> SubscriptionLifecycleView:
        business: BusinessDocument = input_data.business
        language: LanguageTag = input_data.display_language or business.owner_language
        policy: SubscriptionLifecyclePolicy = self._lifecycle_policy_registry.policy()
        subscription: SubscriptionDocument | None = find_current_subscription(
            self._subscription_repo, business.id
        )
        invoices: list[InvoiceDocument] = (
            []
            if subscription is None
            else list_subscription_invoices(self._invoice_repo, subscription)
        )
        pause: PauseAvailability = read_pause_availability(
            business,
            subscription,
            invoices,
            self._subscription_event_repo.list_by_business(business.id),
            policy,
            self._app_settings.growth.is_subscription_pause_enabled,
        )
        inputs: OfferInputs = gather_offer_inputs(
            subscription,
            pause,
            self._billing_credit_repo.list_by_business(business.id),
            self._plan_registry,
            policy,
        )
        offers: list[CancellationOfferView] = []
        for reason in CancellationReason:
            kind: RetentionOfferKind | None = offer_for(reason, policy, inputs)
            offers.append(
                CancellationOfferView(
                    reason=reason,
                    offer=None
                    if kind is None
                    else view_offer(
                        kind, inputs, language, self._localized_text_resolver
                    ),
                )
            )

        return SubscriptionLifecycleView(
            business_id=business.id,
            pause=view_pause(inputs, policy, language, business.timezone),
            offers=offers,
        )
