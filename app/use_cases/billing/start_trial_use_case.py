from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.businesses import ServiceMode
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.billing import PlanDefinition
from app.schemas.dto.billing_cabinet import (
    BillingOverview,
    BillingOverviewSource,
    StartTrialCommand,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.use_cases.billing.billing_records import is_trial_available
from app.use_cases.billing.trial_subscriptions import open_trial_subscription


class StartTrialUseCase(UseCaseContract[StartTrialCommand, BillingOverview]):
    """
    Owner starts the free trial (concept: 14 days), once per business.

    The subscription is TRIALING until `trial_ends_at` and is priced in the
    business currency when the price book has it (GEL in Georgia), otherwise
    in EUR; the trial itself is free, nothing is invoiced yet. The chosen
    plan becomes the business plan and the assistant serves in full.

    A subscription chosen without a trial and never paid (INCOMPLETE)
    becomes the trial: its unpaid bills are voided.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
        business_repo: BusinessRepoContract,
        plan_registry: PlanRegistryContract,
        assemble_billing_overview: UseCaseContract[
            BillingOverviewSource,
            BillingOverview,
        ],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._plan_registry: PlanRegistryContract = plan_registry
        self._assemble_billing_overview: UseCaseContract[
            BillingOverviewSource,
            BillingOverview,
        ] = assemble_billing_overview
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: StartTrialCommand) -> BillingOverview:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        if not is_trial_available(
            self._subscription_repo.list_by_business(business.id)
        ):
            raise ConflictError("The free trial of this business was already used.")

        plan_key: PlanKey = input_data.request.plan_key or business.plan_key
        plan: PlanDefinition = self._plan_registry.get(plan_key)
        if int(plan.trial_days) == 0:
            raise ValidationFailedError(f"Plan {plan_key.value} has no free trial.")

        now: Microseconds = self._wall_clock.now_unix()
        open_trial_subscription(
            self._subscription_repo,
            self._invoice_repo,
            self._plan_registry,
            business,
            plan_key,
            input_data.request.billing_period,
            now,
        )

        def start_trial(current: BusinessDocument) -> None:
            # Changed on the business as stored now, so an edit saved
            # meanwhile is kept.
            current.plan_key = plan_key
            current.service_mode = ServiceMode.FULL
            current.updated_at = now

        business = self._business_repo.update(business.id, start_trial)
        return self._assemble_billing_overview.run(
            BillingOverviewSource(
                business=business,
                display_language=input_data.display_language,
            )
        )
