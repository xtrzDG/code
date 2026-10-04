"""One client's summary for the platform admin."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.billing_repositories import (
    OnboardingRequestRepoContract,
    SubscriptionRepoContract,
    UsageEventRepoContract,
)
from app.contracts.repositories.booking_repositories import (
    HandoffRepoContract,
    UnansweredQuestionRepoContract,
)
from app.contracts.repositories.conversation_repositories import MessageRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.client_health import ClientHealthIssue, ClientHealthStatus
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.admin import (
    AdminClientSummary,
    ClientAutotestVerdict,
    ClientSummarySource,
    OnboardingRequestView,
)
from app.schemas.dto.billing import PlanDefinition
from app.schemas.dto.billing_ledger import (
    ClientCostQuery,
    ClientCostReport,
    PackageUsageTotals,
)
from app.schemas.typings.client_health.constrained_integers import (
    HandoffCount,
    OpenQuestionCount,
    ToolErrorCount,
)
from app.schemas.typings.conversations.constrained_integers import (
    ReplyLatencyMilliseconds,
)
from app.use_cases.admin.active_version import (
    count_failed_scenarios,
    find_active_version,
    read_client_verdict,
)
from app.use_cases.admin.client_health_rules import find_health_issues, judge_health
from app.use_cases.admin.client_usage_window import (
    MICROSECONDS_PER_DAY,
    find_client_usage_window,
)
from app.use_cases.shared.billing_records import find_current_subscription
from app.use_cases.shared.package_usage import summarize_package_usage
from app.utilities.client_health.reply_speed import (
    REPLY_LATENCY_BUCKET_STARTS,
    build_client_reply_speed,
)

RECENT_ACTIVITY_DAYS: int = 7
REPLY_LATENCY_BUCKETS: tuple[ReplyLatencyMilliseconds, ...] = tuple(
    ReplyLatencyMilliseconds(start) for start in REPLY_LATENCY_BUCKET_STARTS
)


class SummarizeClientUseCase(UseCaseContract[ClientSummarySource, AdminClientSummary]):
    """
    One client as the platform admin sees it (concept section 8, /admin).

    Subscription and service mode; the published assistant version; the
    autotest verdict of the active version (the published one, else the
    latest tested) exactly as the version stores it; handoffs and tool errors
    of the last 7 days; how long customers waited for replies in the last
    7 days (p50 and p95 per channel) and what the reply guard did (replies
    rewritten or handed over, messages flagged as prompt injection); open
    unanswered questions; package
    use, provider cost and margin in the current billing window (the last
    30 days without a subscription); and the health verdict. Leads-only service and a
    negative margin are critical; other issues ask for attention. Sandbox
    (test chat) handoffs and questions are not counted. Every count is a
    database count or an indexed read of the few matching documents, so a
    summary costs the same whatever the client's history.
    """

    def __init__(
        self,
        subscription_repo: SubscriptionRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        handoff_repo: HandoffRepoContract,
        unanswered_question_repo: UnansweredQuestionRepoContract,
        message_repo: MessageRepoContract,
        usage_event_repo: UsageEventRepoContract,
        onboarding_request_repo: OnboardingRequestRepoContract,
        plan_registry: PlanRegistryContract,
        compute_client_cost: UseCaseContract[ClientCostQuery, ClientCostReport],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._handoff_repo: HandoffRepoContract = handoff_repo
        self._unanswered_question_repo: UnansweredQuestionRepoContract = (
            unanswered_question_repo
        )
        self._message_repo: MessageRepoContract = message_repo
        self._usage_event_repo: UsageEventRepoContract = usage_event_repo
        self._onboarding_request_repo: OnboardingRequestRepoContract = (
            onboarding_request_repo
        )
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
        active_version: AssistantVersionDocument | None = find_active_version(
            self._assistant_version_repo, business
        )
        published_version: AssistantVersionDocument | None = (
            active_version
            if active_version is not None
            and active_version.id == business.published_assistant_version_id
            else None
        )
        verdict: ClientAutotestVerdict | None = read_client_verdict(active_version)
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
            setup_option=None if subscription is None else subscription.setup_option,
            onboarding_request=self._onboarding_request(business),
            published_version_number=(
                None if published_version is None else published_version.version_number
            ),
            published_at=(
                None if published_version is None else published_version.published_at
            ),
            last_test_score=None if verdict is None else verdict.average_score,
            failed_tests=count_failed_scenarios(verdict),
            autotest_verdict=verdict,
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
            reply_speed=build_client_reply_speed(
                self._message_repo.count_reply_latencies(
                    business.id, recent_since, REPLY_LATENCY_BUCKETS
                )
            ),
            guard_activity=self._message_repo.count_guard_activity(
                business.id, recent_since
            ),
            health_status=ClientHealthStatus.HEALTHY,
        )
        issues: list[ClientHealthIssue] = find_health_issues(summary, subscription)
        return summary.model_copy(
            update={
                "health_issues": issues,
                "health_status": judge_health(issues),
            }
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

    def _onboarding_request(
        self, business: BusinessDocument
    ) -> OnboardingRequestView | None:
        request = self._onboarding_request_repo.get_by_business(business.id)
        if request is None:
            return None

        return OnboardingRequestView(
            status=request.status,
            plan_key=request.plan_key,
            requested_at=request.requested_at,
        )
