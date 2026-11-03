from base_pydantic_schemas import BaseDocument, PersistentDocument, SchemaVersion
from typed_time_provider import Microseconds

from app.schemas.constants.campaigns import (
    CampaignAudience,
    CampaignMessageStatus,
    CampaignSkipReason,
    RebookingRuleKind,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.campaigns.booleans import IsCampaignEnabled
from app.schemas.typings.campaigns.constrained_integers import (
    CampaignMessageCount,
    CampaignMonthlyCap,
    RebookingDelayDays,
)
from app.schemas.typings.campaigns.constrained_strings import CampaignMonthKey
from app.schemas.typings.campaigns.prefixed_id import (
    CampaignMessageId,
    CampaignSettingsId,
)
from app.schemas.typings.contacts.prefixed_id import ContactId, CustomerSegmentId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.deliveries.prefixed_id import OutboundMessageId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId

DEFAULT_MONTHLY_CAP: CampaignMonthlyCap = CampaignMonthlyCap(100)


class CampaignReviewHold(PersistentDocument):
    """
    The campaign is held for the platform team's review (ABUSE-05): too
    many of the customers it wrote to in the last 30 days asked for no
    more messages (`opted_out` of `sent`, measured `held_at`). It sends
    nothing until a platform admin releases it; the owner's settings stay
    as they are.
    """

    held_at: Microseconds
    sent: CampaignMessageCount
    opted_out: CampaignMessageCount


class CampaignSettingsDocument(BaseDocument):
    """
    The rebooking campaign of one business (Bookings → Return visits; one
    document per business, the id derived from it). Off until the owner
    turns it on (`is_enabled`): then the rule (`rule_kind` with
    `delay_days`, from the niche's default until the owner changes it)
    writes to the customers it finds, or only to the members of the saved
    segment `segment_id` (`audience`), at most `monthly_cap` messages in a
    calendar month of the business. STOP, the suppression list and a
    blocked customer always win.

    Version 2 adds `review_hold` (optional, ABUSE-05): set by the campaign
    job when the opt-out rate of its recent messages is too high, cleared
    by a platform admin; the owner's saves keep it. Version 3 adds
    `review_released_at` (optional): when a platform admin last released a
    hold; the campaign's opt-out rate counts only the messages sent since,
    so the messages that held it cannot hold it again.
    """

    schema_version: SchemaVersion = SchemaVersion("3")
    id: CampaignSettingsId
    business_id: BusinessId
    is_enabled: IsCampaignEnabled = False
    rule_kind: RebookingRuleKind
    delay_days: RebookingDelayDays
    audience: CampaignAudience = CampaignAudience.ALL_CUSTOMERS
    segment_id: CustomerSegmentId | None = None
    monthly_cap: CampaignMonthlyCap = DEFAULT_MONTHLY_CAP
    updated_by: UserId | None = None
    review_hold: CampaignReviewHold | None = None
    review_released_at: Microseconds | None = None


class CampaignMessageDocument(BaseDocument):
    """
    One message of a business's campaign to one customer, about one booking
    (`anchor_booking_id`: the last visit an invitation back follows, or the
    booking a pre-arrival note is about); the id derives from the business,
    the rule and that booking, so it is written once.

    A SENT message went into the outbox in `channel` and `language` and
    counts against the cap of its `month`; when the customer books again
    within a week of it, it becomes BOOKED (`booking_id`, `booked_at`) and
    the booking is marked as a campaign booking. A SKIPPED one keeps why.
    """

    id: CampaignMessageId
    business_id: BusinessId
    contact_id: ContactId
    rule_kind: RebookingRuleKind
    anchor_booking_id: BookingId
    status: CampaignMessageStatus
    skip_reason: CampaignSkipReason | None = None
    month: CampaignMonthKey
    language: LanguageTag
    channel: ChannelKind | None = None
    conversation_id: ConversationId | None = None
    outbound_message_id: OutboundMessageId | None = None
    sent_at: Microseconds | None = None
    booking_id: BookingId | None = None
    booked_at: Microseconds | None = None
