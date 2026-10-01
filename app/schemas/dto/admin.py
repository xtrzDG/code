"""Platform admin: every client with health, usage and margin (concept /admin)."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AutotestOutcome, AutotestScenarioKind
from app.schemas.constants.billing import (
    BillingPeriod,
    InvoiceKind,
    InvoiceStatus,
    PlanKey,
    SubscriptionStatus,
)
from app.schemas.constants.businesses import BusinessStatus, ServiceMode
from app.schemas.constants.client_health import (
    CabinetSection,
    ClientHealthIssue,
    ClientHealthStatus,
)
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.payments import PaymentStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.billing import Money
from app.schemas.dto.billing_ledger import ClientCostReport
from app.schemas.typings.assistants.constrained_floats import AverageJudgeScore
from app.schemas.typings.assistants.constrained_integers import (
    AssistantVersionNumber,
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
from app.schemas.typings.compliance.prefixed_id import AuditLogEntryId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.users.prefixed_id import UserId


class AdminClientsQuery(ImmutableDTO):
    """A platform admin lists every client."""

    user_id: UserId


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


class AdminClientList(ImmutableDTO):
    """Every client, the ones needing attention first."""

    generated_at: Microseconds
    client_count: ClientCount
    clients: list[AdminClientSummary]


class FailedAutotestView(ImmutableDTO):
    """A scenario that did not pass in the latest autotest run."""

    scenario_key: AutotestScenarioKey
    kind: AutotestScenarioKind
    language: LanguageTag
    outcome: AutotestOutcome
    judge_notes: list[JudgeNote] = Field(default_factory=list[JudgeNote])


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
