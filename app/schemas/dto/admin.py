"""Platform admin: every client with health, usage and margin (concept /admin)."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import (
    AutotestCheckCode,
    AutotestOutcome,
    AutotestScenarioKind,
    JudgeCriterion,
)
from app.schemas.constants.billing import (
    BillingPeriod,
    InvoiceKind,
    InvoiceStatus,
    PlanKey,
    SubscriptionStatus,
)
from app.schemas.constants.businesses import BusinessStatus, ServiceMode
from app.schemas.constants.client_health import (
    AdminClientSort,
    CabinetSection,
    ClientHealthIssue,
    ClientHealthStatus,
)
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.payments import PaymentStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.billing import Money
from app.schemas.dto.billing_ledger import ClientCostReport
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.assistants.booleans import IsAutotestRunPassed
from app.schemas.typings.assistants.constrained_floats import AverageJudgeScore
from app.schemas.typings.assistants.constrained_integers import (
    AssistantVersionNumber,
    AutotestScenarioCount,
)
from app.schemas.typings.assistants.constrained_strings import AutotestScenarioKey
from app.schemas.typings.assistants.strings import JudgeNote
from app.schemas.typings.billing.booleans import IsAutoDebitActive, IsRefundDue
from app.schemas.typings.billing.constrained_integers import (
    IncludedDialogs,
    IncludedVoiceMinutes,
    UsedDialogs,
    UsedVoiceMinutes,
)
from app.schemas.typings.billing.prefixed_id import InvoiceId, PaymentOrderId
from app.schemas.typings.billing.strings import PaymentFailureReason
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.client_health.constrained_integers import (
    AutotestFailureCount,
    ClientCount,
    HandoffCount,
    OpenQuestionCount,
    ToolErrorCount,
)
from app.schemas.typings.client_health.constrained_strings import ClientSearchText
from app.schemas.typings.compliance.prefixed_id import AuditLogEntryId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId


class AdminClientsQuery(ImmutableDTO):
    """
    A platform admin lists clients, one page at a time, in the chosen
    order. Filters (business status, health, country, niche, search in the
    name or id) run before paging.
    """

    user_id: UserId
    page: PageRequest = PageRequest()
    status: BusinessStatus | None = None
    health: ClientHealthStatus | None = None
    country_code: CountryCode | None = None
    niche_key: NicheKey | None = None
    search: ClientSearchText | None = None
    sort: AdminClientSort = AdminClientSort.HEALTH


class AdminClientQuery(ImmutableDTO):
    """A platform admin looks at one client."""

    user_id: UserId
    business_id: BusinessId


class OpenClientCabinetCommand(ImmutableDTO):
    """A platform admin enters a client's cabinet; always audited."""

    user_id: UserId
    business_id: BusinessId
    client_ip_address: ClientIpAddress | None = None


class ClientSummarySource(ImmutableDTO):
    """A business to summarize for an already authorized platform admin."""

    business: BusinessDocument


class ClientAutotestVerdict(ImmutableDTO):
    """
    The autotest verdict of the client's active version (the published one,
    else the latest tested), exactly as the version stores it, so the admin
    and the version page never disagree. Counts are None for a version
    tested before verdicts were stored: its status says passed or not.
    """

    version_number: AssistantVersionNumber
    is_passed: IsAutotestRunPassed
    passed_count: AutotestScenarioCount | None = None
    scenario_count: AutotestScenarioCount | None = None
    average_score: AverageJudgeScore | None = None


class AdminClientSummary(ImmutableDTO):
    """
    One client in the admin list: subscription, assistant quality, staff
    load, package use in the current period, cost and margin, and health.
    """

    business_id: BusinessId
    name: BusinessName
    country_code: CountryCode
    niche_key: NicheKey
    currency_code: CurrencyCode
    business_status: BusinessStatus
    service_mode: ServiceMode
    plan_key: PlanKey
    subscription_status: SubscriptionStatus | None = None
    billing_period: BillingPeriod | None = None
    period_end: Microseconds | None = None
    grace_until: Microseconds | None = None
    has_auto_debit: IsAutoDebitActive = False
    published_version_number: AssistantVersionNumber | None = None
    published_at: Microseconds | None = None
    last_test_score: AverageJudgeScore | None = None
    failed_tests: AutotestFailureCount
    autotest_verdict: ClientAutotestVerdict | None = None
    handoffs_last_7_days: HandoffCount
    tool_errors_last_7_days: ToolErrorCount
    open_unanswered_questions: OpenQuestionCount
    used_voice_minutes: UsedVoiceMinutes
    included_voice_minutes: IncludedVoiceMinutes
    used_dialogs: UsedDialogs
    included_dialogs: IncludedDialogs
    cost: ClientCostReport
    health_status: ClientHealthStatus
    health_issues: list[ClientHealthIssue] = Field(
        default_factory=list[ClientHealthIssue]
    )


class AdminClientTotals(ImmutableDTO):
    """Counts over every client of the platform, whatever the filters."""

    client_count: ClientCount
    critical_count: ClientCount
    attention_count: ClientCount
    healthy_count: ClientCount
    losing_money_count: ClientCount


class AdminClientPage(ImmutableDTO):
    """
    One page of clients; `next_cursor` is None on the last page.

    `matching_count` counts the clients that pass the filters; `totals`,
    `countries` and `niches` describe every client (for the summary tiles
    and the filter choices).
    """

    generated_at: Microseconds
    items: list[AdminClientSummary]
    next_cursor: PageCursor | None = None
    matching_count: ClientCount
    totals: AdminClientTotals
    countries: list[CountryCode] = Field(default_factory=list[CountryCode])
    niches: list[NicheKey] = Field(default_factory=list[NicheKey])


class FailedAutotestView(ImmutableDTO):
    """
    A scenario that did not pass in the run of the active version's verdict.
    Why, as codes every language renders: the harness checks that failed
    (`check_codes`) and the judge's criteria scored below 3
    (`low_criteria`). `judge_notes` is the judge's own text (English).
    """

    scenario_key: AutotestScenarioKey
    kind: AutotestScenarioKind
    language: LanguageTag
    outcome: AutotestOutcome
    judge_notes: list[JudgeNote] = Field(default_factory=list[JudgeNote])
    check_codes: list[AutotestCheckCode] = Field(
        default_factory=list[AutotestCheckCode]
    )
    low_criteria: list[JudgeCriterion] = Field(default_factory=list[JudgeCriterion])


class AdminInvoiceView(ImmutableDTO):
    """An invoice of the client as the admin sees it."""

    id: InvoiceId
    kind: InvoiceKind
    amount: Money
    status: InvoiceStatus
    period_start: Microseconds
    period_end: Microseconds


class AdminPaymentView(ImmutableDTO):
    """A checkout at the payment provider and how it ended."""

    id: PaymentOrderId
    status: PaymentStatus
    amount: Money
    created_at: Microseconds
    failure_reason: PaymentFailureReason | None = None
    is_refund_due: IsRefundDue = False


class ClientHealthView(ImmutableDTO):
    """One client in detail: the summary plus what explains it."""

    summary: AdminClientSummary
    timezone: TimezoneName
    failed_autotests: list[FailedAutotestView] = Field(
        default_factory=list[FailedAutotestView]
    )
    invoices: list[AdminInvoiceView] = Field(default_factory=list[AdminInvoiceView])
    payments: list[AdminPaymentView] = Field(default_factory=list[AdminPaymentView])


class ClientCabinetAccess(ImmutableDTO):
    """
    What a platform admin may now open in the client's cabinet. Every later
    cabinet request of the admin is audited again by the access check.
    """

    business_id: BusinessId
    business_name: BusinessName
    country_code: CountryCode
    owner_language: LanguageTag
    sections: list[CabinetSection]
    audit_log_entry_id: AuditLogEntryId
    opened_at: Microseconds
