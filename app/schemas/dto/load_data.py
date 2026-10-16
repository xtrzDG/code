"""
Load-test datasets (`workshop seed-load`, tests/perf, perf/k6): what to
store, how one business's share is built, and the manifest the load tests
read (business ids, owner bearer tokens, widget visitors, webhook paths).

Every load business is a demo business (foundation, assembled assistant
versions, a month of demo activity) under its own owner, plus a bulk
history: contacts, conversations with their messages, bookings and
website-widget visitors.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.demo_data import DemoBusinessFoundation
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import (
    TelegramWebhookSecret,
    WidgetSessionKey,
)
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId
from app.schemas.typings.demo.constrained_integers import (
    LoadBookingCount,
    LoadBusinessCount,
    LoadBusinessIndex,
    LoadMessageCount,
    LoadRandomSeed,
    LoadVisitorCount,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessToken


class SeedLoadCommand(ImmutableDTO):
    """
    Store a load-test dataset of this size. The defaults are the weekly
    perf run's scale: 500 businesses, 2M messages, 200k bookings and 1000
    widget visitors.
    """

    business_count: LoadBusinessCount = LoadBusinessCount(500)
    message_count: LoadMessageCount = LoadMessageCount(2_000_000)
    booking_count: LoadBookingCount = LoadBookingCount(200_000)
    visitor_count: LoadVisitorCount = LoadVisitorCount(1_000)
    random_seed: LoadRandomSeed = LoadRandomSeed(7)


class LoadBusinessShare(ImmutableDTO):
    """One business's part of the dataset's volume."""

    message_count: LoadMessageCount
    booking_count: LoadBookingCount
    visitor_count: LoadVisitorCount


class LoadBusinessPlan(ImmutableDTO):
    """A load business before it is stored: its demo foundation and owner."""

    index: LoadBusinessIndex
    owner_id: UserId
    owner_access_token: AccessToken
    foundation: DemoBusinessFoundation
    share: LoadBusinessShare
    random_seed: LoadRandomSeed


class LoadSeedPlan(ImmutableDTO):
    """Every load business of the run, its owners already signed in."""

    seeded_at: Microseconds
    businesses: list[LoadBusinessPlan] = Field(default_factory=list[LoadBusinessPlan])


class LoadVolumeStorage(ImmutableDTO):
    """A stored load business whose bulk history is to be stored."""

    plan: LoadBusinessPlan
    seeded_at: Microseconds


class LoadVolumeRequest(ImmutableDTO):
    """What the bulk history of one business is built from."""

    business: BusinessDocument
    resources: list[ResourceDocument]
    # The business's chat channels customers write in (no phone line).
    channel_kinds: list[ChannelKind]
    assistant_version_id: AssistantVersionId
    model_id: LlmModelId
    share: LoadBusinessShare
    random_seed: LoadRandomSeed
    now: Microseconds


class LoadWidgetVisitor(ImmutableDTO):
    """
    A website-widget visitor with a conversation: the load test polls with
    its session key after its latest message.
    """

    session_key: WidgetSessionKey
    conversation_id: ConversationId
    latest_message_id: MessageId


class LoadVolume(ImmutableDTO):
    """The bulk history of one business, oldest conversations first."""

    contacts: list[ContactDocument]
    conversations: list[ConversationDocument]
    messages: list[MessageDocument]
    bookings: list[BookingDocument]
    visitors: list[LoadWidgetVisitor] = Field(default_factory=list[LoadWidgetVisitor])


class LoadBusinessSeed(ImmutableDTO):
    """
    One stored load business as the load tests address it: the owner's
    bearer token, recent conversations, widget visitors and, for a business
    with a Telegram bot, its webhook channel and secret token.
    """

    business_id: BusinessId
    owner_access_token: AccessToken
    conversation_ids: list[ConversationId]
    visitors: list[LoadWidgetVisitor]
    telegram_channel_id: ChannelId | None = None
    telegram_webhook_secret: TelegramWebhookSecret | None = None
    message_count: LoadMessageCount
    booking_count: LoadBookingCount


class LoadSeedManifest(ImmutableDTO):
    """What `workshop seed-load` stored, written as JSON for the load tests."""

    seeded_at: Microseconds
    businesses: list[LoadBusinessSeed] = Field(default_factory=list[LoadBusinessSeed])
