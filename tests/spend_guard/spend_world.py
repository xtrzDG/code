"""
A business, its owner, its usage events and the spend guard over in-memory
collections, with fixed prices: EUR -> USD at 1.20, so the Chat plan's
planned daily cost is exactly $0.80 (20 EUR / 30 days * 1.2).
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.contracts.repositories.spend_guard_repositories import (
    SpendLimitMarkRepoContract,
    UsageSpendRepoContract,
)
from app.facilitators.spend_guard.spend_limit_notice_facilitator import (
    SpendLimitNoticeFacilitator,
)
from app.repositories.billing_repositories import UsageEventRepository
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.spend_guard_repositories import (
    BusinessLimitsRepository,
    SpendLimitMarkRepository,
    UsageSpendRepository,
)
from app.repositories.user_repositories import UserRepository
from app.schemas.configurations.platform_alert_settings import PlatformAlertSettings
from app.schemas.configurations.spend_guard_settings import SpendGuardSettings
from app.schemas.constants.billing import PlanKey, UsageKind
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.users import BusinessMemberRole, LoginMethod
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.business_limits import (
    BusinessLimitsDocument,
    SpendLimitMarkDocument,
)
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.catalog.plan_quotes import ExchangeRateQuote
from app.schemas.dto.spend_guard import UsageKindTotal
from app.schemas.typings.billing.constrained_integers import (
    CostMicroUsd,
    UsageQuantity,
)
from app.schemas.typings.billing.constrained_strings import (
    ExchangeRateDate,
    ExchangeRateValue,
)
from app.schemas.typings.billing.strings import ExchangeRateSourceName
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.monitoring.constrained_strings import AlertChatId
from app.schemas.typings.spend.constrained_integers import DailySpendLimitMicroUsd
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.spend_guard.check_business_spend_use_case import (
    CheckBusinessSpendUseCase,
)
from app.utilities.spend.spend_keys import business_limits_id_of
from tests.knowledge.website_import.recording_job_queue import RecordingJobQueue
from tests.operations.fakes import FakeLocalizedTextResolver, RecordingManagerNotifier

# Monday 2026-10-05 12:00 in Tbilisi (UTC+4): the business's day began at
# 2026-10-04 20:00 UTC.
NOON: datetime = datetime.fromisoformat("2026-10-05T12:00:00+04:00")
DAY_START: datetime = datetime.fromisoformat("2026-10-05T00:00:00+04:00")
DOLLAR: int = 1_000_000
CHAT_PLANNED_DAILY_MICRO_USD: int = 800_000
TEAM_CHAT: AlertChatId = AlertChatId("-1001234567890")


def micros(moment: datetime) -> Microseconds:
    return Microseconds(int(moment.timestamp()) * 1_000_000)


class FixedEuroRates(ExchangeRateRegistryContract):
    """EUR -> USD at exactly 1.20; no other pair."""

    def find_rate(
        self, base_currency_code: CurrencyCode, quote_currency_code: CurrencyCode
    ) -> ExchangeRateQuote | None:
        if (str(base_currency_code), str(quote_currency_code)) != ("EUR", "USD"):
            return None

        return ExchangeRateQuote(
            base_currency_code=base_currency_code,
            quote_currency_code=quote_currency_code,
            rate_value=ExchangeRateValue("1.2"),
            rate_date=ExchangeRateDate("2026-10-02"),
            source=ExchangeRateSourceName("European Central Bank"),
        )


@dataclass
class SpendWorld:
    business: BusinessDocument
    owner: UserDocument
    usage_events: UsageEventRepository
    limits: BusinessLimitsRepository
    marks: SpendLimitMarkRepository
    audit: AuditLogRepository
    notifier: RecordingManagerNotifier
    jobs: RecordingJobQueue
    check: CheckBusinessSpendUseCase
    usage_spend: CountingUsageSpend

    def spend(
        self,
        kind: UsageKind,
        quantity: int,
        cost_micro_usd: int,
        at: datetime = NOON,
    ) -> None:
        moment = micros(at)
        self.usage_events.append(
            UsageEventDocument(
                business_id=self.business.id,
                kind=kind,
                quantity=UsageQuantity(quantity),
                cost_micro_usd=CostMicroUsd(cost_micro_usd),
                occurred_at=moment,
                created_at=moment,
                updated_at=moment,
            )
        )

    def set_limits(self, soft: int | None, hard: int | None) -> None:
        self.limits.save(
            BusinessLimitsDocument(
                id=business_limits_id_of(self.business.id),
                business_id=self.business.id,
                daily_soft_limit_micro_usd=(
                    None if soft is None else DailySpendLimitMicroUsd(soft)
                ),
                daily_hard_limit_micro_usd=(
                    None if hard is None else DailySpendLimitMicroUsd(hard)
                ),
            )
        )

    def audit_entries(self) -> list[AuditLogEntryDocument]:
        return self.audit.list_by_business(self.business.id)


class CountingUsageSpend(UsageSpendRepoContract):
    """The real sums, counted, so a test sees when the guard skips them."""

    def __init__(self, inner: UsageSpendRepoContract) -> None:
        self._inner: UsageSpendRepoContract = inner
        self.business_sums: int = 0

    def sum_business(
        self,
        business_id: BusinessId,
        occurred_from: Microseconds,
        occurred_to: Microseconds,
    ) -> list[UsageKindTotal]:
        self.business_sums += 1
        return self._inner.sum_business(business_id, occurred_from, occurred_to)

    def sum_platform(
        self, occurred_from: Microseconds, occurred_to: Microseconds
    ) -> list[UsageKindTotal]:
        return self._inner.sum_platform(occurred_from, occurred_to)


def build_business(owner_id: UserId, plan_key: PlanKey) -> BusinessDocument:
    return BusinessDocument(
        name=BusinessName("Salobie Bia"),
        niche_key=NicheKey.RESTAURANT,
        country_code=CountryCode("GE"),
        timezone=TimezoneName("Asia/Tbilisi"),
        currency_code=CurrencyCode("GEL"),
        languages=[LanguageTag("ka"), LanguageTag("en")],
        default_language=LanguageTag("ka"),
        owner_language=LanguageTag("ka"),
        plan_key=plan_key,
        data_region=DataRegion.EU,
        members=[BusinessMember(user_id=owner_id, role=BusinessMemberRole.OWNER)],
    )


def build_spend_world(
    plan_key: PlanKey = PlanKey.CHAT,
    settings: SpendGuardSettings | None = None,
    wrap_marks: Callable[[SpendLimitMarkRepoContract], SpendLimitMarkRepoContract]
    | None = None,
) -> SpendWorld:
    owner = UserDocument(
        login_method=LoginMethod.EMAIL,
        email=EmailAddress("owner@salobie.example"),
        locale=LanguageTag("ru"),
    )
    users = UserRepository(InMemoryDocumentCollectionAdapter(UserDocument))
    users.save(owner)
    business = build_business(owner.id, plan_key)
    usage_collection = InMemoryDocumentCollectionAdapter(UsageEventDocument)
    usage_spend = CountingUsageSpend(UsageSpendRepository(usage_collection))
    limits = BusinessLimitsRepository(
        InMemoryDocumentCollectionAdapter(BusinessLimitsDocument)
    )
    marks = SpendLimitMarkRepository(
        InMemoryDocumentCollectionAdapter(SpendLimitMarkDocument)
    )
    audit = AuditLogRepository(InMemoryDocumentCollectionAdapter(AuditLogEntryDocument))
    notifier = RecordingManagerNotifier()
    jobs = RecordingJobQueue()
    check = CheckBusinessSpendUseCase(
        business_limits_repo=limits,
        spend_limit_mark_repo=marks if wrap_marks is None else wrap_marks(marks),
        usage_spend_repo=usage_spend,
        user_repo=users,
        audit_log_repo=audit,
        notices=SpendLimitNoticeFacilitator(
            manager_notifier=notifier,
            job_queue=jobs,
            localized_text_resolver=FakeLocalizedTextResolver(),
            alert_settings=PlatformAlertSettings(telegram_chat_ids=[TEAM_CHAT]),
        ),
        exchange_rate_registry=FixedEuroRates(),
        settings=settings or SpendGuardSettings(),
    )
    return SpendWorld(
        business=business,
        owner=owner,
        usage_events=UsageEventRepository(usage_collection),
        limits=limits,
        marks=marks,
        audit=audit,
        notifier=notifier,
        jobs=jobs,
        check=check,
        usage_spend=usage_spend,
    )
