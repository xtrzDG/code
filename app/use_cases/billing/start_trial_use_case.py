from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories import BusinessRepoContract, SubscriptionRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import PlanKey, SubscriptionStatus
from app.schemas.constants.businesses import ServiceMode
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.billing import Money, PlanDefinition
from app.schemas.dto.billing_cabinet import (
    BillingOverview,
    BillingOverviewSource,
    StartTrialCommand,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.use_cases.billing.subscription_pricing import (
    price_subscription,
    select_subscription_currency,
)
from app.utilities.billing.billing_periods import add_local_days


class StartTrialUseCase(UseCaseContract[StartTrialCommand, BillingOverview]):
    """
    Owner starts the free trial (concept: 14 days), once per business.

    The subscription is TRIALING until `trial_ends_at` and is priced in the
    business currency when the price book has it (GEL in Georgia), otherwise
    in EUR; the trial itself is free, nothing is invoiced yet. The chosen
    plan becomes the business plan and the assistant serves in full.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        subscription_repo: SubscriptionRepoContract,
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
        if self._subscription_repo.list_by_business(business.id) != []:
            raise ConflictError("The free trial of this business was already used.")

        plan_key: PlanKey = input_data.request.plan_key or business.plan_key
        plan: PlanDefinition = self._plan_registry.get(plan_key)
        if int(plan.trial_days) == 0:
            raise ValidationFailedError(f"Plan {plan_key.value} has no free trial.")

        currency_code: CurrencyCode = select_subscription_currency(
            self._plan_registry,
            plan_key,
            business.currency_code,
        )
        price: Money = price_subscription(
            self._plan_registry,
            plan_key,
            input_data.request.billing_period,
            currency_code,
        )
        now: Microseconds = self._wall_clock.now_unix()
        trial_ends_at: Microseconds = add_local_days(
            now,
            int(plan.trial_days),
            business.timezone,
        )
        self._subscription_repo.save(
            SubscriptionDocument(
                business_id=business.id,
                plan_key=plan_key,
                billing_period=input_data.request.billing_period,
                price_minor=price.amount_minor,
                currency_code=price.currency_code,
                status=SubscriptionStatus.TRIALING,
                trial_ends_at=trial_ends_at,
                period_start=now,
                period_end=trial_ends_at,
                created_at=now,
                updated_at=now,
            )
        )
        business.plan_key = plan_key
        business.service_mode = ServiceMode.FULL
        business.updated_at = now
        self._business_repo.save(business)
        return self._assemble_billing_overview.run(
            BillingOverviewSource(
                business=business,
                display_language=input_data.display_language,
            )
        )
