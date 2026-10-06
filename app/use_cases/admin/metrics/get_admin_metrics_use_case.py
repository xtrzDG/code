from typed_time_provider import Microseconds, WallClock

from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.contracts.repositories.analytics_repositories import (
    ProductEventRepoContract,
    WebVitalSampleRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.subscription_event_repositories import (
    SubscriptionEventRepoContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.analytics import ProductEventName, WebVitalName
from app.schemas.constants.subscription_lifecycle import SubscriptionEventKind
from app.schemas.domain.product_events import ProductEventDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.analytics.admin_metrics_query import AdminMetricsQuery
from app.schemas.dto.analytics.admin_metrics_view import AdminMetricsView, WebVitalView
from app.schemas.dto.analytics.growth_views import GrowthView
from app.schemas.dto.analytics.revenue_views import RevenueView
from app.schemas.dto.billing_ledger import ClientCostQuery, ClientCostReport
from app.schemas.dto.catalog.plan_quotes import ExchangeRateQuote
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.typings.analytics.constrained_integers import OwnerCount
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.admin.metrics.business_growth import (
    admin_exclusion,
    build_business_growth,
    count_excluded_businesses,
)
from app.use_cases.admin.metrics.margin_summary import summarize_margin
from app.use_cases.admin.metrics.metrics_period import MetricsPeriod, resolve_period
from app.use_cases.admin.metrics.metrics_scope import (
    business_ids,
    business_scope,
    filter_choices,
    keeps_owner,
    owner_sources,
)
from app.use_cases.shared.business_walk import walk_businesses
from app.utilities.analytics.activation_math import (
    build_activation,
    build_trial_conversion,
)
from app.utilities.analytics.churn_math import build_churn
from app.utilities.analytics.cohort_math import build_cohorts, build_sources
from app.utilities.analytics.euro_conversion import euro_converter, rates_to_euro
from app.utilities.analytics.funnel_math import (
    build_funnel,
    build_tunnel,
    median_time_to_live,
)
from app.utilities.analytics.mrr_math import (
    BILLING_EVENTS,
    build_mrr,
    paying_businesses_at,
)
from app.utilities.analytics.owner_journeys import (
    BusinessRoster,
    build_business_journeys,
    build_owner_journeys,
    invited_member_ids,
    roster_of,
)
from app.utilities.analytics.web_vital_math import bucket_starts, build_web_vitals

# The steps after sign-up the funnel, tunnel, activation and trials read
# (from the period's start on); billing steps are read from the beginning.
JOURNEY_EVENTS: tuple[ProductEventName, ...] = tuple(
    name
    for name in ProductEventName
    if name not in BILLING_EVENTS
    and name not in {ProductEventName.SIGNED_IN, ProductEventName.PAYMENT_FAILED}
)


class GetAdminMetricsUseCase(UseCaseContract[AdminMetricsQuery, AdminMetricsView]):
    """
    The founder's growth metrics (platform admins only), from first-party
    data: the funnel of the period's sign-ups (owners, not invited staff or
    admins), their median time to go live, activation within a week,
    trial-to-paid conversion, where the tunnel lost owners, monthly
    cohorts and acquisition sources; MRR at the start and end of the period
    with its movements, ARPA and gross margin in euros (official rates);
    why owners cancelled, the offers and pauses that kept them and the
    win-back messages (`churn_math.py`); and the cabinet's Web Vitals.
    Filters by country, niche and source.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        user_repo: UserRepoContract,
        business_repo: BusinessRepoContract,
        product_event_repo: ProductEventRepoContract,
        web_vital_sample_repo: WebVitalSampleRepoContract,
        compute_client_cost: UseCaseContract[ClientCostQuery, ClientCostReport],
        exchange_rate_registry: ExchangeRateRegistryContract,
        wall_clock: WallClock[Microseconds],
        subscription_event_repo: SubscriptionEventRepoContract,
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._user_repo: UserRepoContract = user_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._product_event_repo: ProductEventRepoContract = product_event_repo
        self._web_vital_sample_repo: WebVitalSampleRepoContract = web_vital_sample_repo
        self._compute_client_cost: UseCaseContract[
            ClientCostQuery, ClientCostReport
        ] = compute_client_cost
        self._exchange_rate_registry: ExchangeRateRegistryContract = (
            exchange_rate_registry
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._subscription_event_repo: SubscriptionEventRepoContract = (
            subscription_event_repo
        )

    def run(self, input_data: AdminMetricsQuery) -> AdminMetricsView:
        self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.VIEW_METRICS,
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        period: MetricsPeriod = resolve_period(
            input_data.period_start, input_data.period_end, now
        )
        after_now = Microseconds(int(now) + 1)
        billing: list[ProductEventDocument] = self._product_event_repo.list_named(
            BILLING_EVENTS, None, after_now
        )
        events: list[ProductEventDocument] = [
            *self._product_event_repo.list_named(
                JOURNEY_EVENTS, period.start, after_now
            ),
            *billing,
        ]
        # Only each business's roster is kept, never its whole document.
        businesses: list[BusinessRoster] = [
            roster_of(business) for business in walk_businesses(self._business_repo)
        ]
        signed_up: list[UserDocument] = self._user_repo.list_created_between(
            period.start, period.end
        )
        business_journeys = build_business_journeys(businesses, events)
        owner_ids: list[UserId] = sorted(
            {b.owner_id for b in business_journeys if b.owner_id is not None}, key=str
        )
        business_owners: list[UserDocument] = self._user_repo.get_many(owner_ids)
        exclusion = admin_exclusion(
            [*signed_up, *business_owners], input_data.include_platform_admins
        )
        every_owner = build_owner_journeys(
            signed_up,
            business_journeys,
            invited_member_ids(businesses),
            events,
            include_platform_admins=True,
        )
        owners = exclusion.owners(every_owner)
        cohort = [owner for owner in owners if keeps_owner(owner, input_data)]
        sources = owner_sources(business_owners)
        in_scope = business_scope(business_journeys, sources, input_data)
        return AdminMetricsView(
            generated_at=now,
            period_start=period.first_day,
            period_end=period.last_day,
            growth=GrowthView(
                funnel=build_funnel(cohort),
                median_time_to_live_seconds=median_time_to_live(cohort),
                activation=build_activation(in_scope, period.start, period.end, now),
                trials=build_trial_conversion(in_scope, period.start, period.end, now),
                tunnel=build_tunnel(cohort),
                cohorts=build_cohorts(cohort, billing, now),
                sources=build_sources(cohort, paying_businesses_at(billing, now)),
                businesses=build_business_growth(
                    in_scope, business_journeys, events, cohort, period, exclusion
                ),
                are_platform_admins_included=exclusion.is_included,
                excluded_platform_admins=OwnerCount(len(every_owner) - len(owners)),
                excluded_admin_businesses=count_excluded_businesses(
                    in_scope, period, exclusion
                ),
            ),
            revenue=RevenueView(
                mrr=build_mrr(
                    billing,
                    business_ids(in_scope),
                    period.start,
                    min(period.end, after_now, key=int),
                    euro_converter(self._exchange_rate_registry),
                ).model_copy(
                    update={"rates": self._rates(billing, business_ids(in_scope))}
                ),
                margin=summarize_margin(
                    sorted(business_ids(in_scope), key=str),
                    period.start,
                    min(period.end, after_now, key=int),
                    self._compute_client_cost,
                    self._exchange_rate_registry,
                ),
            ),
            web_vitals=self._web_vitals(period),
            choices=filter_choices(business_journeys, owners, sources),
            churn=build_churn(
                [
                    step
                    for kind in SubscriptionEventKind
                    for step in self._subscription_event_repo.list_of_kind(
                        kind, period.start, min(period.end, after_now, key=int)
                    )
                ],
                billing,
                business_ids(in_scope),
            ),
        )

    def _rates(
        self, billing: list[ProductEventDocument], in_scope: set[BusinessId]
    ) -> list[ExchangeRateQuote]:
        """The rates the period's billing currencies were turned into euros with."""

        return rates_to_euro(
            self._exchange_rate_registry,
            [
                event.properties.currency_code
                for event in billing
                if event.properties.currency_code is not None
                and event.business_id in in_scope
            ],
        )

    def _web_vitals(self, period: MetricsPeriod) -> list[WebVitalView]:
        return [
            view
            for metric in WebVitalName
            for view in build_web_vitals(
                metric,
                self._web_vital_sample_repo.count_buckets(
                    metric, period.start, period.end, bucket_starts(metric)
                ),
            )
        ]
