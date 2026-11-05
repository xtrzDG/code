from typed_time_provider import Microseconds

from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.contracts.platform_safety import (
    PlatformPauseRepoContract,
    PlatformSpendGaugeContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.customer_memory_repositories import (
    AssistantSettingsRepoContract,
)
from app.contracts.repositories.spend_guard_repositories import (
    BusinessLimitsRepoContract,
    SpendLimitMarkRepoContract,
    UsageSpendRepoContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.spend_guard import SpendLimitNoticeFacilitatorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.spend_guard_settings import SpendGuardSettings
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.spend import SpendLevel
from app.schemas.domain.business_limits import SpendLimitMarkDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.platform_pause import PlatformBrakeReading
from app.schemas.dto.spend_guard import (
    ProviderSpend,
    SpendCheckRequest,
    SpendLimitPassing,
    SpendLimits,
    SpendVerdict,
)
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.spend.constrained_integers import DailySpendLimitMicroUsd
from app.schemas.typings.spend.prefixed_id import SpendLimitMarkId
from app.use_cases.shared.owner_contacts import owner_contacts
from app.use_cases.spend_guard.monthly_spend_limit import (
    business_month_start,
    monthly_hard_limit,
    monthly_mark_id_of,
)
from app.utilities.spend.cheaper_models import cheaper_model_of
from app.utilities.spend.platform_brakes import (
    read_platform_brake,
)
from app.utilities.spend.spend_days import business_day
from app.utilities.spend.spend_keys import spend_limit_mark_id_of
from app.utilities.spend.spend_limit_defaults import resolve_spend_limits
from app.utilities.spend.spend_pricing import price_usage, total_spend

AUDITED_ENTITY: AuditEntityName = AuditEntityName("business")


class CheckBusinessSpendUseCase(UseCaseContract[SpendCheckRequest, SpendVerdict]):
    """
    Where a business's provider spend of its own day (midnight to now in its
    time zone) stands against its daily limits, before each model turn and
    each call.

    Spend is summed by the database from today's usage events and priced by
    provider (`spend_pricing`: recorded costs, planned unit prices where a
    figure is missing). The limits are the business's own (`business_limits`,
    set by the platform team) or multiples of its plan's planned daily
    provider cost. Past the soft limit the verdict names the cheaper model
    of the turn's provider; past the hard one the business only takes
    messages for its team until its midnight.

    The first process to see a limit passed on a day stores its mark (an
    insert that only one of several racing processes wins) and only that
    one tells the owners and the platform team (`SpendLimitNoticeFacilitator`)
    and, for the hard limit, writes SPEND_LIMIT_REACHED to the business's
    audit log. A hard mark of the day for the current limit settles later
    turns with one read by id; raising the limit lets the business answer
    again the same day.

    On top of the day, the business's month has a hard limit too
    (`monthly_spend_limit`): a business kept just under its daily limit day
    after day stops at it until its month ends, marked, audited and told
    once like the daily one.

    First of all the platform's own brakes (`read_platform_brake`): while a
    platform admin paused every assistant, or the platform's provider
    spend of the UTC day reached its daily budget stop, every business is
    at HARD_LIMIT: its turns go to the team (the customer hears, in their
    language, that a colleague takes over) and its
    calls to the forwarding number. Nothing is marked, audited or told per
    business (the platform alerts tell the team about the stop; the pause
    is audited where it is set). Then the owner's own pause (Settings →
    General, AI-10): while it holds, the business is at HARD_LIMIT the
    same way, until the owner resumes it.
    """

    def __init__(
        self,
        business_limits_repo: BusinessLimitsRepoContract,
        spend_limit_mark_repo: SpendLimitMarkRepoContract,
        usage_spend_repo: UsageSpendRepoContract,
        user_repo: UserRepoContract,
        audit_log_repo: AuditLogRepoContract,
        notices: SpendLimitNoticeFacilitatorContract,
        exchange_rate_registry: ExchangeRateRegistryContract,
        settings: SpendGuardSettings,
        platform_pause_repo: PlatformPauseRepoContract,
        platform_spend_gauge: PlatformSpendGaugeContract,
        assistant_settings_repo: AssistantSettingsRepoContract,
    ) -> None:
        self._limits_repo: BusinessLimitsRepoContract = business_limits_repo
        self._marks: SpendLimitMarkRepoContract = spend_limit_mark_repo
        self._usage: UsageSpendRepoContract = usage_spend_repo
        self._user_repo: UserRepoContract = user_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._notices: SpendLimitNoticeFacilitatorContract = notices
        self._exchange_rates: ExchangeRateRegistryContract = exchange_rate_registry
        self._settings: SpendGuardSettings = settings
        self._pause_repo: PlatformPauseRepoContract = platform_pause_repo
        self._spend_gauge: PlatformSpendGaugeContract = platform_spend_gauge
        self._assistant_settings_repo: AssistantSettingsRepoContract = (
            assistant_settings_repo
        )

    def run(self, input_data: SpendCheckRequest) -> SpendVerdict:
        business: BusinessDocument = input_data.business
        day, day_started_at = business_day(input_data.now, business.timezone)
        limits: SpendLimits = resolve_spend_limits(
            self._limits_repo.get_or_default(business.id),
            business.plan_key,
            self._settings,
            self._exchange_rates,
        )
        brake: PlatformBrakeReading = read_platform_brake(
            self._pause_repo, self._spend_gauge, self._settings, input_data.now
        )
        if brake.brake is not None or self._is_paused_by_owner(business):
            return SpendVerdict(
                level=SpendLevel.HARD_LIMIT,
                day=day,
                spend_micro_usd=CostMicroUsd(0),
                limits=limits,
            )
        hard_mark: SpendLimitMarkDocument | None = self._marks.get(
            business.id,
            spend_limit_mark_id_of(business.id, day, SpendLevel.HARD_LIMIT),
        )
        if hard_mark is not None and int(hard_mark.limit_micro_usd) >= int(
            limits.hard_limit_micro_usd
        ):
            return SpendVerdict(
                level=SpendLevel.HARD_LIMIT,
                day=day,
                spend_micro_usd=hard_mark.spend_micro_usd,
                limits=limits,
            )

        month, month_started_at = business_month_start(
            input_data.now, business.timezone
        )
        month_limit: DailySpendLimitMicroUsd = monthly_hard_limit(limits)
        month_mark_id: SpendLimitMarkId = monthly_mark_id_of(business.id, month)
        month_mark: SpendLimitMarkDocument | None = self._marks.get(
            business.id, month_mark_id
        )
        if month_mark is not None and int(month_mark.limit_micro_usd) >= int(
            month_limit
        ):
            return SpendVerdict(
                level=SpendLevel.HARD_LIMIT,
                day=day,
                spend_micro_usd=month_mark.spend_micro_usd,
                limits=limits,
            )

        providers: list[ProviderSpend] = price_usage(
            self._usage.sum_business(
                business.id, day_started_at, Microseconds(int(input_data.now) + 1)
            )
        )
        spend: CostMicroUsd = total_spend(providers)
        level: SpendLevel = level_of(spend, limits)
        if level is not SpendLevel.HARD_LIMIT and int(spend) > 0:
            month_providers: list[ProviderSpend] = price_usage(
                self._usage.sum_business(
                    business.id,
                    month_started_at,
                    Microseconds(int(input_data.now) + 1),
                )
            )
            month_spend: CostMicroUsd = total_spend(month_providers)
            if int(month_spend) >= int(month_limit):
                passing = SpendLimitPassing(
                    business=business,
                    level=SpendLevel.HARD_LIMIT,
                    day=day,
                    spend_micro_usd=month_spend,
                    limit_micro_usd=month_limit,
                    providers=month_providers,
                    is_monthly=True,
                )
                self._mark_once(passing, month_mark_id, input_data.now)
                return SpendVerdict(
                    level=SpendLevel.HARD_LIMIT,
                    day=day,
                    spend_micro_usd=month_spend,
                    limits=limits,
                )

        if level is not SpendLevel.NORMAL:
            self._mark_once(
                SpendLimitPassing(
                    business=business,
                    level=level,
                    day=day,
                    spend_micro_usd=spend,
                    limit_micro_usd=(
                        limits.hard_limit_micro_usd
                        if level is SpendLevel.HARD_LIMIT
                        else limits.soft_limit_micro_usd
                    ),
                    providers=providers,
                ),
                spend_limit_mark_id_of(business.id, day, level),
                input_data.now,
            )

        return SpendVerdict(
            level=level,
            day=day,
            spend_micro_usd=spend,
            limits=limits,
            cheaper_model_id=(
                cheaper_model_of(
                    input_data.model_id, self._settings.soft_limit_model_id
                )
                if level is SpendLevel.SOFT_LIMIT and input_data.model_id is not None
                else None
            ),
        )

    def _is_paused_by_owner(self, business: BusinessDocument) -> bool:
        settings = self._assistant_settings_repo.get_by_business(business.id)
        return settings is not None and settings.is_paused

    def _mark_once(
        self, passing: SpendLimitPassing, mark_id: SpendLimitMarkId, now: Microseconds
    ) -> None:
        """
        Store the limit's mark; the one process that stores it tells the
        owners and the team and audits a hard limit.
        """

        business: BusinessDocument = passing.business
        mark = SpendLimitMarkDocument(
            id=mark_id,
            business_id=business.id,
            day=passing.day,
            level=passing.level,
            spend_micro_usd=passing.spend_micro_usd,
            limit_micro_usd=passing.limit_micro_usd,
            reached_at=now,
            created_at=now,
            updated_at=now,
        )
        if not self._marks.insert_if_absent(mark):
            return

        if passing.level is SpendLevel.HARD_LIMIT:
            self._audit_log_repo.append(
                AuditLogEntryDocument(
                    business_id=business.id,
                    action=AuditAction.SPEND_LIMIT_REACHED,
                    entity=AUDITED_ENTITY,
                    entity_id=AuditEntityReference(str(business.id)),
                    created_at=now,
                    updated_at=now,
                )
            )

        self._notices.announce(passing, owner_contacts(business, self._user_repo))


def level_of(spend: CostMicroUsd, limits: SpendLimits) -> SpendLevel:
    """HARD_LIMIT from the hard limit on, SOFT_LIMIT from the soft one."""

    if int(spend) >= int(limits.hard_limit_micro_usd):
        return SpendLevel.HARD_LIMIT

    if int(spend) >= int(limits.soft_limit_micro_usd):
        return SpendLevel.SOFT_LIMIT

    return SpendLevel.NORMAL
