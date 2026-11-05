"""Bookings → Return visits: the rebooking campaign's settings and its messages."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.campaigns import (
    CampaignAudience,
    CampaignMessageStatus,
    CampaignSkipReason,
    RebookingRuleKind,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.growth.growth_counts import CampaignStatusCount
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.campaigns.booleans import IsCampaignEnabled
from app.schemas.typings.campaigns.constrained_integers import (
    CampaignMessageCount,
    CampaignMonthlyCap,
    RebookingDelayDays,
)
from app.schemas.typings.campaigns.prefixed_id import CampaignMessageId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.contacts.constrained_strings import SegmentName
from app.schemas.typings.contacts.prefixed_id import ContactId, CustomerSegmentId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId


class CampaignSettingsRequest(ImmutableDTO):
    """
    The owner's choices: run the campaign, its rule and days, who it may
    write to (everyone the rule finds, or one saved segment) and the most
    messages a calendar month.
    """

    is_enabled: IsCampaignEnabled = False
    rule_kind: RebookingRuleKind
    delay_days: RebookingDelayDays
    audience: CampaignAudience = CampaignAudience.ALL_CUSTOMERS
    segment_id: CustomerSegmentId | None = None
    monthly_cap: CampaignMonthlyCap = CampaignMonthlyCap(100)


class CampaignSettingsQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId


class UpdateCampaignSettingsCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    request: CampaignSettingsRequest


class CampaignMessagePreview(ImmutableDTO):
    """The message of the rule in one language, as a customer reads it."""

    language: LanguageTag
    text: MessageText


class CampaignSettingsView(ImmutableDTO):
    """
    The settings (the niche's rule until the owner changes it), the
    niche's own rule, this month's messages against the cap, the last
    30 days by status, and the message in each language of the business.
    """

    is_enabled: IsCampaignEnabled
    rule_kind: RebookingRuleKind
    delay_days: RebookingDelayDays
    audience: CampaignAudience
    segment_id: CustomerSegmentId | None = None
    segment_name: SegmentName | None = None
    monthly_cap: CampaignMonthlyCap
    niche_rule_kind: RebookingRuleKind
    niche_delay_days: RebookingDelayDays
    month_sent_count: CampaignMessageCount
    recent_counts: list[CampaignStatusCount] = Field(
        default_factory=list[CampaignStatusCount]
    )
    previews: list[CampaignMessagePreview] = Field(
        default_factory=list[CampaignMessagePreview]
    )


class CampaignMessagePageQuery(ImmutableDTO):
    """The campaign's latest messages, newest first (owners, audited)."""

    user_id: UserId
    business_id: BusinessId
    page: PageRequest = PageRequest()
    client_ip_address: ClientIpAddress | None = None


class CampaignMessageView(ImmutableDTO):
    """One customer the campaign wrote to (or skipped, and why) and what followed."""

    id: CampaignMessageId
    contact_id: ContactId
    contact_name: ContactName | None = None
    rule_kind: RebookingRuleKind
    status: CampaignMessageStatus
    skip_reason: CampaignSkipReason | None = None
    channel: ChannelKind | None = None
    conversation_id: ConversationId | None = None
    sent_at: Microseconds | None = None
    booking_id: BookingId | None = None
    booked_at: Microseconds | None = None
    created_at: Microseconds


class CampaignMessagePage(ImmutableDTO):
    items: list[CampaignMessageView]
    next_cursor: PageCursor | None = None
