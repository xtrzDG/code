"""
Development demo data (SEED_DEMO_DATA): what the demo catalog describes and
what seeding reports.

A business is described in two parts. The foundation (business, profile,
knowledge, resources, channels and the history of assistant versions) is
stored first; its versions are assembled from it like an owner would. The
activity (customers, conversations, bookings, leads, handoffs, billing) is
built next, pinned to the published version.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import MessageAuthor, ReplyGuardVerdict
from app.schemas.constants.demo import DemoBusinessKey
from app.schemas.constants.reply_safety import ReplyGuardReason
from app.schemas.domain.assistants import AutotestRunDocument
from app.schemas.domain.billing import (
    InvoiceDocument,
    SubscriptionDocument,
    UsageEventDocument,
)
from app.schemas.domain.billing_profiles import BillingProfileDocument
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.campaigns import (
    CampaignMessageDocument,
    CampaignSettingsDocument,
)
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversation_quality import ConversationQualityScoreDocument
from app.schemas.domain.conversation_topics import ConversationTopicsDocument
from app.schemas.domain.conversations import (
    CallDocument,
    ClaimFinding,
    ConversationDocument,
    MessageDocument,
    ToolCallRecord,
)
from app.schemas.domain.feedback import FeedbackRequestDocument, ReviewSettingsDocument
from app.schemas.domain.handoffs import HandoffDocument, UnansweredQuestionDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.message_media import MessageAttachment, MessageMediaDocument
from app.schemas.domain.package_usage import PackageUsageWarningDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ResourceDocument, ScheduleExceptionDocument
from app.schemas.domain.users import UserDocument
from app.schemas.domain.waitlist import WaitlistEntryDocument
from app.schemas.typings.assistants.constrained_floats import AverageJudgeScore
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.conversations.strings import (
    MessageText,
    UnverifiedReplyValue,
)
from app.schemas.typings.demo.constrained_integers import DemoReplyPauseSeconds
from app.schemas.typings.users.prefixed_id import UserId


class SeedDemoDataCommand(ImmutableDTO):
    """Fill the instance with the demo businesses unless they exist."""


class DemoDataSeedReport(ImmutableDTO):
    """
    What seeding did: the demo owner, the businesses it created and the
    demo businesses that already existed (left as they are).
    """

    owner_id: UserId
    created_business_ids: list[BusinessId] = Field(default_factory=list[BusinessId])
    kept_business_ids: list[BusinessId] = Field(default_factory=list[BusinessId])


class DemoAccounts(ImmutableDTO):
    """The demo owner and the restaurant's staff member, as new accounts."""

    owner: UserDocument
    staff: UserDocument


class DemoFoundationRequest(ImmutableDTO):
    """Accounts the demo businesses belong to and the moment of seeding."""

    owner_id: UserId
    staff_id: UserId
    now: Microseconds


class DemoAssistantVersionPlan(ImmutableDTO):
    """
    One assistant version of the demo history, oldest first. Exactly one
    is PUBLISHED; its autotest run comes with the activity.
    """

    status: AssistantVersionStatus
    created_at: Microseconds
    published_at: Microseconds | None = None
    test_score: AverageJudgeScore | None = None
    voice_agent_id: VoiceAgentId | None = None


class DemoChannelCredential(ImmutableDTO):
    """A made-up channel credential, stored encrypted like a real one."""

    channel: ChannelKind
    secret: ChannelSecret


class DemoBusinessFoundation(ImmutableDTO):
    """What an owner sets up before going live."""

    key: DemoBusinessKey
    business: BusinessDocument
    profile: BusinessProfileDocument
    knowledge_items: list[KnowledgeItemDocument]
    resources: list[ResourceDocument]
    schedule_exceptions: list[ScheduleExceptionDocument] = Field(
        default_factory=list[ScheduleExceptionDocument]
    )
    channels: list[ChannelDocument]
    channel_credentials: list[DemoChannelCredential] = Field(
        default_factory=list[DemoChannelCredential]
    )
    assistant_versions: list[DemoAssistantVersionPlan]


class DemoActivityRequest(ImmutableDTO):
    """
    The stored foundation, the ids its assistant versions got (in the order
    of `foundation.assistant_versions`; a conversation is pinned to the
    version that was live when it started) and the model they answer with.
    """

    foundation: DemoBusinessFoundation
    version_ids: list[AssistantVersionId]
    model_id: LlmModelId
    now: Microseconds


class DemoAttachmentLine(ImmutableDTO):
    """
    An attachment of a demo customer message as the assistant read it, and
    for a voice note or photo the file to store (`content`).
    """

    attachment: MessageAttachment
    content: bytes | None = Field(default=None, repr=False)


class DemoReplyGuard(ImmutableDTO):
    """
    What the reply guard did with a demo assistant reply, as the live engine
    stores it: rewritten once (with what the first draft got wrong) or held
    back and handed to staff (with the values or claims it held back).
    """

    verdict: ReplyGuardVerdict
    reasons: list[ReplyGuardReason] = Field(default_factory=list[ReplyGuardReason])
    unverified_values: list[UnverifiedReplyValue] = Field(
        default_factory=list[UnverifiedReplyValue]
    )
    claim_findings: list[ClaimFinding] = Field(default_factory=list[ClaimFinding])


class DemoMessageLine(ImmutableDTO):
    """
    One message of a demo conversation, `pause_seconds` after the last; an
    assistant reply the guard rewrote or held back carries `guard` (none:
    the guard let it through as written).
    """

    author: MessageAuthor
    text: MessageText
    tool_calls: list[ToolCallRecord] = Field(default_factory=list[ToolCallRecord])
    attachments: list[DemoAttachmentLine] = Field(
        default_factory=list[DemoAttachmentLine]
    )
    pause_seconds: DemoReplyPauseSeconds = DemoReplyPauseSeconds(40)
    guard: DemoReplyGuard | None = None


class DemoMediaFile(ImmutableDTO):
    """A voice note or photo a demo customer sent, with its bytes."""

    media: MessageMediaDocument
    content: bytes = Field(repr=False)


class DemoBusinessActivity(ImmutableDTO):
    """A month of customers and staff work around one business."""

    contacts: list[ContactDocument]
    conversations: list[ConversationDocument]
    messages: list[MessageDocument]
    calls: list[CallDocument] = Field(default_factory=list[CallDocument])
    bookings: list[BookingDocument]
    leads: list[LeadDocument] = Field(default_factory=list[LeadDocument])
    handoffs: list[HandoffDocument] = Field(default_factory=list[HandoffDocument])
    unanswered_questions: list[UnansweredQuestionDocument] = Field(
        default_factory=list[UnansweredQuestionDocument]
    )
    subscription: SubscriptionDocument
    billing_profile: BillingProfileDocument | None = None
    invoices: list[InvoiceDocument] = Field(default_factory=list[InvoiceDocument])
    usage_events: list[UsageEventDocument] = Field(
        default_factory=list[UsageEventDocument]
    )
    package_usage_warnings: list[PackageUsageWarningDocument] = Field(
        default_factory=list[PackageUsageWarningDocument]
    )
    audit_log_entries: list[AuditLogEntryDocument] = Field(
        default_factory=list[AuditLogEntryDocument]
    )
    autotest_run: AutotestRunDocument
    review_settings: ReviewSettingsDocument | None = None
    feedback_requests: list[FeedbackRequestDocument] = Field(
        default_factory=list[FeedbackRequestDocument]
    )
    media_files: list[DemoMediaFile] = Field(default_factory=list[DemoMediaFile])
    conversation_topics: ConversationTopicsDocument | None = None
    quality_scores: list[ConversationQualityScoreDocument] = Field(
        default_factory=list[ConversationQualityScoreDocument]
    )
    waitlist_entries: list[WaitlistEntryDocument] = Field(
        default_factory=list[WaitlistEntryDocument]
    )
    campaign_settings: CampaignSettingsDocument | None = None
    campaign_messages: list[CampaignMessageDocument] = Field(
        default_factory=list[CampaignMessageDocument]
    )


class DemoSeedPlan(ImmutableDTO):
    """
    The demo accounts (found or created) and the demo businesses still to
    create; demo businesses the owner already has are kept as they are.
    """

    owner_id: UserId
    staff_id: UserId
    seeded_at: Microseconds
    foundations: list[DemoBusinessFoundation] = Field(
        default_factory=list[DemoBusinessFoundation]
    )
    kept_business_ids: list[BusinessId] = Field(default_factory=list[BusinessId])


class DemoActivityStorage(ImmutableDTO):
    """A stored demo foundation with the ids its assembled versions got."""

    foundation: DemoBusinessFoundation
    version_ids: list[AssistantVersionId]
    seeded_at: Microseconds
