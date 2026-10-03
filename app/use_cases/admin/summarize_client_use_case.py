"""One client's summary for the platform admin."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
    AutotestRunRepoContract,
)
from app.contracts.repositories.billing_repositories import (
    SubscriptionRepoContract,
    UsageEventRepoContract,
)
from app.contracts.repositories.booking_repositories import (
    HandoffRepoContract,
    UnansweredQuestionRepoContract,
)
from app.contracts.repositories.conversation_repositories import MessageRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AutotestOutcome
from app.schemas.constants.client_health import ClientHealthIssue, ClientHealthStatus
from app.schemas.domain.assistants import AssistantVersionDocument, AutotestRunDocument
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.admin import AdminClientSummary, ClientSummarySource
from app.schemas.dto.billing import PlanDefinition
from app.schemas.dto.billing_ledger import (
    ClientCostQuery,
    ClientCostReport,
    PackageUsageTotals,
)
from app.schemas.typings.client_health.constrained_integers import (
    AutotestFailureCount,
    HandoffCount,
    OpenQuestionCount,
    ToolErrorCount,
)
from app.use_cases.admin.client_health_rules import find_health_issues, judge_health
from app.use_cases.admin.client_usage_window import (
    MICROSECONDS_PER_DAY,
    find_client_usage_window,
)
from app.use_cases.shared.billing_records import find_current_subscription
from app.use_cases.shared.package_usage import summarize_package_usage

RECENT_ACTIVITY_DAYS: int = 7


class SummarizeClientUseCase(UseCaseContract[ClientSummarySource, AdminClientSummary]):
    """
    One client as the platform admin sees it (concept section 8, /admin).

    Subscription and service mode; the published assistant version; the
    latest autotest score and its failed scenarios; handoffs and tool errors
    of the last 7 days; open unanswered questions; package use, provider
    cost and margin in the current billing window (the last 30 days without
    a subscription); and the health verdict. Leads-only service and a
    negative margin are critical; other issues ask for attention. Sandbox
    (test chat) handoffs and questions are not counted. Every count is a
    database count or an indexed read of the few matching documents, so a
    summary costs the same whatever the client's history.
    """

    def __init__(
        self,
        subscription_repo: SubscriptionRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        autotest_run_repo: AutotestRunRepoContract,
        handoff_repo: HandoffRepoContract,
        unanswered_question_repo: UnansweredQuestionRepoContract,
        message_repo: MessageRepoContract,
        usage_event_repo: UsageEventRepoContract,
        plan_registry: PlanRegistryContract,
        compute_client_cost: UseCaseContract[ClientCostQuery, ClientCostReport],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._autotest_run_repo: AutotestRunRepoContract = autotest_run_repo
        self._handoff_repo: HandoffRepoContract = handoff_repo
        self._unanswered_question_repo: UnansweredQuestionRepoContract = (
            unanswered_question_repo
        )
        self._message_repo: MessageRepoContract = message_repo
        self._usage_event_repo: UsageEventRepoContract = usage_event_repo
        self._plan_registry: PlanRegistryContract = plan_registry
        self._compute_client_cost: UseCaseContract[
            ClientCostQuery,
            ClientCostReport,
        ] = compute_client_cost
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ClientSummarySource) -> AdminClientSummary:
        business: BusinessDocument = input_data.business
        now: Microseconds = self._wall_clock.now_unix()
        subscription: SubscriptionDocument | None = find_current_subscription(
            self._subscription_repo,
            business.id,
        )
        plan: PlanDefinition = self._plan_registry.get(
            business.plan_key if subscription is None else subscription.plan_key
        )
        window_start, window_end = find_client_usage_window(business, subscription, now)
        usage: PackageUsageTotals = summarize_package_usage(
            self._usage_event_repo.list_by_business_between(
                business.id,
                window_start,
                window_end,
            ),
            window_start,
            window_end,
        )
        cost: ClientCostReport = self._compute_client_cost.run(
            ClientCostQuery(
                business_id=business.id,
                period_start=window_start,
                period_end=window_end,
            )
        )
        published_version: AssistantVersionDocument | None = self._find_published(
            business
        )
        tested_version: AssistantVersionDocument | None = self._find_last_tested(
            business
        )
        recent_since: Microseconds = Microseconds(
            int(now) - RECENT_ACTIVITY_DAYS * MICROSECONDS_PER_DAY
        )
        summary = AdminClientSummary(
            business_id=business.id,
            name=business.name,
            country_code=business.country_code,
            niche_key=business.niche_key,
            currency_code=business.currency_code,
            business_status=business.status,
            service_mode=business.service_mode,
            plan_key=plan.key,
            subscription_status=None if subscription is None else subscription.status,
            billing_period=None
            if subscription is None
            else subscription.billing_period,
            period_end=None if subscription is None else subscription.period_end,
            grace_until=None if subscription is None else subscription.grace_until,
            has_auto_debit=(
                subscription is not None and subscription.provider_reference is not None
            ),
            published_version_number=(
                None if published_version is None else published_version.version_number
            ),
            published_at=(
                None if published_version is None else published_version.published_at
            ),
            last_test_score=None
            if tested_version is None
            else tested_version.test_score,
            failed_tests=self._count_failed_tests(business, tested_version),
            handoffs_last_7_days=self._count_recent_handoffs(business, recent_since),
            tool_errors_last_7_days=self._count_recent_tool_errors(
                business,
                recent_since,
            ),
            open_unanswered_questions=self._count_open_questions(business),
            used_voice_minutes=usage.used_voice_minutes,
            included_voice_minutes=plan.included_voice_minutes,
            used_dialogs=usage.used_dialogs,
            included_dialogs=plan.included_dialogs,
            cost=cost,
            health_status=ClientHealthStatus.HEALTHY,
        )
        issues: list[ClientHealthIssue] = find_health_issues(summary, subscription)
        return summary.model_copy(
            update={
                "health_issues": issues,
                "health_status": judge_health(issues),
            }
        )

    def _find_published(
        self,
        business: BusinessDocument,
    ) -> AssistantVersionDocument | None:
        if business.published_assistant_version_id is None:
            return None

        return self._assistant_version_repo.get(
            business.id,
            business.published_assistant_version_id,
        )

    def _find_last_tested(
        self,
        business: BusinessDocument,
    ) -> AssistantVersionDocument | None:
        tested_versions: list[AssistantVersionDocument] = [
            version
            for version in self._assistant_version_repo.list_by_business(business.id)
            if version.autotest_run_id is not None or version.test_score is not None
        ]
        if tested_versions == []:
            return None

        return max(tested_versions, key=lambda version: version.version_number)

    def _count_failed_tests(
        self,
        business: BusinessDocument,
        tested_version: AssistantVersionDocument | None,
    ) -> AutotestFailureCount:
        if tested_version is None or tested_version.autotest_run_id is None:
            return AutotestFailureCount(0)

        run: AutotestRunDocument | None = self._autotest_run_repo.get(
            business.id,
            tested_version.autotest_run_id,
        )
        if run is None:
            return AutotestFailureCount(0)

        return AutotestFailureCount(
            sum(
                1
                for result in run.results
                if result.outcome is not AutotestOutcome.PASSED
            )
        )

    def _count_recent_handoffs(
        self,
        business: BusinessDocument,
        recent_since: Microseconds,
    ) -> HandoffCount:
        return HandoffCount(
            int(self._handoff_repo.count_made_since(business.id, recent_since))
        )

    def _count_recent_tool_errors(
        self,
        business: BusinessDocument,
        recent_since: Microseconds,
    ) -> ToolErrorCount:
        return ToolErrorCount(
            sum(
                1
                for message in self._message_repo.list_with_tool_errors(
                    business.id, recent_since
                )
                for tool_call in message.tool_calls
                if tool_call.is_error
            )
        )

    def _count_open_questions(self, business: BusinessDocument) -> OpenQuestionCount:
        return OpenQuestionCount(
            int(self._unanswered_question_repo.count_open(business.id))
        )
