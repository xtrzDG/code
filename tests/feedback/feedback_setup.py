"""
A live Georgian business with WhatsApp and Telegram connected, its customer,
their visits and the job that asks how a visit went, over the channels
testbed (its outbox worker delivers through the real platform clients).
"""

from typing import Any

from typed_time_provider import Microseconds

from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.registries.limits.request_rate_limit_registry import RequestRateLimitRegistry
from app.repositories.feedback_repositories import ReviewSettingsRepository
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.feedback import FeedbackRequestDocument, ReviewSettingsDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.assistants.constrained_integers import AssistantVersionNumber
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
)
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.feedback.constrained_integers import FeedbackDelayMinutes
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.platform.constrained_strings import JobName
from app.use_cases.feedback.request.request_visit_feedback_use_case import (
    RequestVisitFeedbackUseCase,
)
from app.utilities.feedback.feedback_keys import review_settings_id_of
from tests.channels.outbox_reads import outbox_of
from tests.channels.testbed import ChannelsTestbed

WHATSAPP_NUMBER_ID: str = "106540352242922"
TEMPLATE_NAME: str = "visit_feedback"
CUSTOMER_PHONE: str = "+995599123456"
WHATSAPP_USER: str = "995599123456"
TELEGRAM_USER: str = "555000111"
SECONDS_PER_MINUTE: int = 60
MICROSECONDS_PER_SECOND: int = 1_000_000
SENT: dict[str, Any] = {"messages": [{"id": "wamid.feedback"}]}


class FeedbackSetup:
    """The business, its feedback settings, rate limits and the job."""

    def __init__(
        self,
        status: BusinessStatus = BusinessStatus.LIVE,
        has_settings: bool = True,
    ) -> None:
        self.testbed = ChannelsTestbed()
        owner_id = self.testbed.add_user("owner")
        self.business: BusinessDocument = self.testbed.add_business(
            owner_id, name="Café Rustaveli"
        )
        version = AssistantVersionDocument(
            business_id=self.business.id,
            version_number=AssistantVersionNumber(1),
            niche_key=NicheKey.RESTAURANT,
            model_id=LlmModelId("gpt-5-mini"),
            prompt_text=SystemPromptText("Prompt"),
            tools=[AssistantToolName.CREATE_BOOKING],
            languages=self.business.languages,
            default_language=self.business.default_language,
            is_voice_enabled=False,
            facts=[],
            profile_revision=Microseconds(1),
        )
        self.testbed.assistant_version_repo.save(version)
        self.business.status = status
        self.business.published_assistant_version_id = version.id
        self.testbed.business_repo.save(self.business)
        self.testbed.add_channel(
            self.business.id, ChannelKind.WHATSAPP, WHATSAPP_NUMBER_ID
        )
        self.testbed.meta_transport.respond("POST", r"/messages$", SENT)
        self.review_settings_repo = ReviewSettingsRepository(
            InMemoryDocumentCollectionAdapter(ReviewSettingsDocument)
        )
        self.rate_limits = RequestRateLimitRegistry(InMemoryRateLimitBucketAdapter())
        self.job = RequestVisitFeedbackUseCase(
            review_settings_repo=self.review_settings_repo,
            feedback_request_repo=self.testbed.feedback_request_repo,
            business_repo=self.testbed.business_repo,
            booking_repo=self.testbed.booking_repo,
            contact_repo=self.testbed.contact_repo,
            channel_repo=self.testbed.channel_repo,
            conversation_repo=self.testbed.conversation_repo,
            message_repo=self.testbed.message_repo,
            outbound_message_repo=self.testbed.outbound_message_repo,
            job_queue=self.testbed.job_queue,
            rate_limits=self.rate_limits,
            text_resolver=self.testbed.text_resolver,
            live_events=self.testbed.live_events,
            wall_clock=self.testbed.wall_clock,
        )
        if has_settings:
            self.save_settings()

    def now_seconds(self) -> int:
        return self.testbed.clock.now_seconds()

    def save_settings(
        self,
        is_enabled: bool = True,
        delay_minutes: int = 120,
        template_name: str | None = TEMPLATE_NAME,
    ) -> None:
        now = self.testbed.clock.now_microseconds()
        self.review_settings_repo.save(
            ReviewSettingsDocument(
                id=review_settings_id_of(self.business.id),
                business_id=self.business.id,
                is_feedback_enabled=is_enabled,
                delay_minutes=FeedbackDelayMinutes(delay_minutes),
                feedback_template_name=(
                    None
                    if template_name is None
                    else WhatsAppTemplateName(template_name)
                ),
                created_at=now,
                updated_at=now,
            )
        )

    def connect_telegram(self) -> None:
        self.testbed.add_channel(self.business.id, ChannelKind.TELEGRAM, "bot", "tok")

    def add_customer(
        self,
        channels: tuple[ChannelKind, ...] = (ChannelKind.WHATSAPP,),
        language: str | None = "ka",
        opted_out: tuple[ChannelKind, ...] = (),
        phone: str = CUSTOMER_PHONE,
    ) -> ContactDocument:
        user_ids: dict[ChannelKind, str] = {
            ChannelKind.WHATSAPP: phone.removeprefix("+"),
            ChannelKind.TELEGRAM: TELEGRAM_USER,
            ChannelKind.PHONE: phone,
        }
        contact = ContactDocument(
            business_id=self.business.id,
            phone_number=E164PhoneNumber(phone),
            language=None if language is None else LanguageTag(language),
            channel_identities=[
                ChannelIdentity(
                    channel=channel, channel_user_id=ChannelUserId(user_ids[channel])
                )
                for channel in channels
            ],
            opted_out_channels=list(opted_out),
        )
        self.testbed.contact_repo.save(contact)
        return contact

    def add_visit(
        self,
        contact: ContactDocument,
        ended_minutes_ago: int = 150,
        status: BookingStatus = BookingStatus.COMPLETED,
        source_channel: ChannelKind = ChannelKind.WHATSAPP,
        is_sandbox: bool = False,
        language: str | None = None,
    ) -> BookingDocument:
        ends_at: int = self.now_seconds() - ended_minutes_ago * SECONDS_PER_MINUTE
        booking = BookingDocument(
            business_id=self.business.id,
            resource_id=ResourceId(),
            contact_id=contact.id,
            starts_at=BookingStartsAtUnixSeconds(ends_at - 2 * 60 * SECONDS_PER_MINUTE),
            ends_at=BookingEndsAtUnixSeconds(ends_at),
            party_size=PartySize(2),
            status=status,
            source_channel=source_channel,
            is_sandbox=is_sandbox,
            language=None if language is None else LanguageTag(language),
        )
        self.testbed.booking_repo.save(booking)
        return booking

    def customer_wrote(
        self, contact: ContactDocument, channel: ChannelKind, hours_ago: float
    ) -> ConversationDocument:
        """The customer's message in a channel some hours before now."""

        moment = Microseconds(
            int(self.testbed.clock.now_microseconds())
            - int(hours_ago * 3600 * MICROSECONDS_PER_SECOND)
        )
        identity = next(
            identity
            for identity in contact.channel_identities
            if identity.channel is channel
        )
        assert self.business.published_assistant_version_id is not None
        conversation = ConversationDocument(
            business_id=self.business.id,
            contact_id=contact.id,
            assistant_version_id=self.business.published_assistant_version_id,
            channel=channel,
            channel_user_id=identity.channel_user_id,
            last_message_at=moment,
            created_at=moment,
            updated_at=moment,
        )
        self.testbed.conversation_repo.save(conversation)
        self.testbed.message_repo.save(
            MessageDocument(
                conversation_id=conversation.id,
                business_id=self.business.id,
                direction=MessageDirection.INBOUND,
                author=MessageAuthor.CUSTOMER,
                text=MessageText("Thanks, see you"),
                created_at=moment,
                updated_at=moment,
            )
        )
        return conversation

    def run(self) -> JobReport:
        return self.job.run(
            JobTick(
                job_name=JobName("request_visit_feedback"),
                scheduled_at=self.testbed.clock.now_microseconds(),
            )
        )

    def requests(self) -> list[FeedbackRequestDocument]:
        """The business's requests for feedback, oldest first."""

        return sorted(
            (
                request
                for request in self.testbed.feedback_request_collection.list_all()
                if request.business_id == self.business.id
            ),
            key=lambda request: (int(request.created_at), str(request.id)),
        )

    def only_request(self) -> FeedbackRequestDocument:
        [request] = self.requests()
        return request

    def outbox(self) -> list[OutboundMessageDocument]:
        return outbox_of(self.testbed, self.business.id)

    def whatsapp_sends(self) -> list[dict[str, Any]]:
        return [
            request.json()
            for request in self.testbed.meta_transport.requests_to("/messages")
        ]
