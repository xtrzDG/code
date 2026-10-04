"""
The founder's metrics over in-memory repositories: owners, their
businesses, product events and Web Vital samples written by hand, client
costs answered by a fake, and the real GetAdminMetricsUseCase.
"""

from dataclasses import dataclass, field
from typing import Any

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.use_case_contract import UseCaseContract
from app.repositories.business_repositories import BusinessRepository
from app.repositories.user_repositories import UserRepository
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.users import BusinessMemberRole, LoginMethod
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.domain.product_events import ProductEventDocument
from app.schemas.domain.signup_attribution import SignupAttribution
from app.schemas.domain.users import UserDocument
from app.schemas.dto.analytics.admin_metrics_query import AdminMetricsQuery
from app.schemas.dto.analytics.admin_metrics_view import AdminMetricsView
from app.schemas.dto.billing import Money
from app.schemas.dto.billing_ledger import ClientCostQuery, ClientCostReport
from app.schemas.typings.billing.constrained_integers import (
    CostMicroUsd,
    MoneyAmountMinor,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    LanguageTag,
    TimezoneName,
)
from app.use_cases.admin.metrics.get_admin_metrics_use_case import (
    GetAdminMetricsUseCase,
)
from tests.analytics.analytics_fakes import (
    SettableClock,
    product_event_repo,
    web_vital_sample_repo,
)
from tests.analytics.metric_events import at_day
from tests.billing.exchange_rate_fixtures import StoredRate, rate_registry
from tests.foundation.access_support import AuthorizeFlaggedAdmin

# Two lari and 1.25 US dollars a euro, so the numbers stay round (no
# fallback catalog: only these rates and their inverses exist).
TEST_RATES: tuple[StoredRate, ...] = (
    ("EUR", "GEL", "2"),
    ("EUR", "USD", "1.25"),
)


@dataclass
class FixedClientCosts(UseCaseContract[ClientCostQuery, ClientCostReport]):
    """Revenue and provider cost of each business, whatever the period."""

    reports: dict[BusinessId, tuple[Money, int]] = field(
        default_factory=dict[BusinessId, tuple[Money, int]]
    )

    def run(self, input_data: ClientCostQuery) -> ClientCostReport:
        revenue, cost = self.reports.get(
            input_data.business_id,
            (
                Money(
                    amount_minor=MoneyAmountMinor(0),
                    currency_code=CurrencyCode("EUR"),
                ),
                0,
            ),
        )
        return ClientCostReport(
            business_id=input_data.business_id,
            period_start=input_data.period_start,
            period_end=input_data.period_end,
            llm_cost_micro_usd=CostMicroUsd(cost),
            provider_cost_micro_usd=CostMicroUsd(cost),
            revenue=revenue,
        )


class MetricsWorld:
    """Owners, businesses and events in memory; the admin reads metrics."""

    def __init__(self, today: float = 44) -> None:
        self.clock = SettableClock(int(at_day(today)))
        self.users = UserRepository(InMemoryDocumentCollectionAdapter(UserDocument))
        self.businesses = BusinessRepository(
            InMemoryDocumentCollectionAdapter(BusinessDocument)
        )
        self.events = product_event_repo()
        self.vitals = web_vital_sample_repo()
        self.costs = FixedClientCosts()
        self.admin = self.add_user(0, is_platform_admin=True)
        self.use_case = GetAdminMetricsUseCase(
            authorize_platform_admin=AuthorizeFlaggedAdmin(self.users),
            user_repo=self.users,
            business_repo=self.businesses,
            product_event_repo=self.events,
            web_vital_sample_repo=self.vitals,
            compute_client_cost=self.costs,
            exchange_rate_registry=rate_registry(TEST_RATES, fallback=()),
            wall_clock=self.clock.wall_clock(),
        )

    def add_user(
        self,
        day: float,
        attribution: SignupAttribution | None = None,
        country: str | None = "GE",
        is_platform_admin: bool = False,
    ) -> UserDocument:
        moment: Microseconds = at_day(day)
        user = UserDocument(
            login_method=LoginMethod.PHONE,
            country_code=None if country is None else CountryCode(country),
            locale=LanguageTag("en"),
            is_platform_admin=is_platform_admin,
            signup_attribution=attribution,
            created_at=moment,
            updated_at=moment,
        )
        self.users.save(user)
        return user

    def add_business(
        self,
        owner: UserDocument,
        day: float,
        country: str = "GE",
        niche: NicheKey = NicheKey.RESTAURANT,
        staff: list[UserDocument] | None = None,
    ) -> BusinessDocument:
        moment: Microseconds = at_day(day)
        business = BusinessDocument(
            name=BusinessName("Salobie Bia"),
            niche_key=niche,
            country_code=CountryCode(country),
            timezone=TimezoneName("Asia/Tbilisi"),
            currency_code=CurrencyCode("GEL"),
            languages=[LanguageTag("en")],
            default_language=LanguageTag("en"),
            owner_language=LanguageTag("en"),
            plan_key=PlanKey.VOICE_AND_CHAT,
            data_region=DataRegion.EU,
            members=[
                BusinessMember(user_id=owner.id, role=BusinessMemberRole.OWNER),
                *(
                    BusinessMember(user_id=person.id, role=BusinessMemberRole.STAFF)
                    for person in staff or []
                ),
            ],
            created_at=moment,
            updated_at=moment,
        )
        self.businesses.save(business)
        return business

    def record(self, *events: ProductEventDocument) -> None:
        for event in events:
            self.events.record(event)

    def metrics(self, **filters: Any) -> AdminMetricsView:
        return self.use_case.run(AdminMetricsQuery(user_id=self.admin.id, **filters))
