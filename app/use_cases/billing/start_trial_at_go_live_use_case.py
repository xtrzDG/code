from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.billing import PlanDefinition
from app.schemas.dto.billing_go_live import GoLiveTrial, GoLiveTrialRequest
from app.use_cases.shared.billing_records import find_current_subscription
from app.use_cases.shared.trial_subscriptions import (
    choose_go_live_trial,
    is_trial_due_at_go_live,
    open_trial_subscription,
)


class StartTrialAtGoLiveUseCase(UseCaseContract[GoLiveTrialRequest, GoLiveTrial]):
    """
    The free trial starts when the assistant first goes live, not when the
    business is created: an owner who spends a week on the setup still gets
    every trial day with customers.

    It starts only while the trial is still available (once per business:
    no subscription yet, or only one chosen without a trial and never paid)
    and the plan has trial days; a trial the owner already started, or a
    paid subscription, is left as it is. The plan is the one of the unpaid
    subscription, else the business plan, billed monthly after the trial.
    Only the subscription is written here; the caller gives the business
    the plan and full service in the same write that makes it live.
    """

    def __init__(
        self,
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
        plan_registry: PlanRegistryContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._plan_registry: PlanRegistryContract = plan_registry
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: GoLiveTrialRequest) -> GoLiveTrial:
        business: BusinessDocument = input_data.business
        plan_key, billing_period = choose_go_live_trial(
            business,
            find_current_subscription(self._subscription_repo, business.id),
        )
        plan: PlanDefinition = self._plan_registry.get(plan_key)
        if not is_trial_due_at_go_live(
            self._subscription_repo.list_by_business(business.id), plan
        ):
            return GoLiveTrial(is_started=False)

        subscription: SubscriptionDocument = open_trial_subscription(
            self._subscription_repo,
            self._invoice_repo,
            self._plan_registry,
            business,
            plan_key,
            billing_period,
            self._wall_clock.now_unix(),
        )
        return GoLiveTrial(
            is_started=True,
            plan_key=plan_key,
            trial_ends_at=subscription.trial_ends_at,
        )
