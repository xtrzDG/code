"""The waitlist's use cases over the growth world, and a customer's turn."""

from datetime import datetime

from typed_time_provider import Microseconds

from app.contracts.use_case_contract import UseCaseContract
from app.gateways.worker.periodic.growth_jobs import EXPIRE_WAITLIST_OFFERS_JOB
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.conversation_engine import TurnGate
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.waitlist import WaitlistEntryDocument, WaitlistSettingsDocument
from app.schemas.dto.assistant_tools import AssistantToolContext
from app.schemas.dto.booking_manage import (
    BookingConfirmationReceipt,
    BookingConfirmationRequest,
)
from app.schemas.dto.conversation_engine import PreparedTurn
from app.schemas.dto.feedback.customer_signals import CustomerSignalReply
from app.schemas.dto.growth.waitlist_joining import (
    JoinWaitlistCommand,
    WaitlistJoinReceipt,
)
from app.schemas.dto.jobs import JobReport, JobTick, QueuedJobInput
from app.schemas.typings.assistants.constrained_integers import AssistantVersionNumber
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.bookings.booleans import IsBookingConfirmationQueued
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.bookings.constrained_strings import (
    LocalDate,
    LocalTimeOfDay,
)
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.waitlist.constrained_integers import WaitlistHoldMinutes
from app.schemas.typings.waitlist.prefixed_id import WaitlistEntryId
from app.use_cases.waitlist.answer_waitlist_offer_use_case import (
    AnswerWaitlistOfferUseCase,
)
from app.use_cases.waitlist.expire_waitlist_offers_use_case import (
    ExpireWaitlistOffersUseCase,
)
from app.use_cases.waitlist.join_waitlist_use_case import JoinWaitlistUseCase
from app.use_cases.waitlist.offer_delivery import WaitlistOfferDelivery
from app.use_cases.waitlist.offer_freed_place_use_case import OfferFreedPlaceUseCase
from app.utilities.waitlist.offer_jobs import OFFER_FREED_PLACE_JOB
from app.utilities.waitlist.waitlist_keys import waitlist_settings_id_of
from tests.operations.builders import DEFAULT_NOW
from tests.waitlist.growth_world import GrowthWorld


class RecordingConfirmations(
    UseCaseContract[BookingConfirmationRequest, BookingConfirmationReceipt]
):
    """The guest's written confirmations, recorded instead of sent."""

    def __init__(self) -> None:
        self.requests: list[BookingConfirmationRequest] = []

    def run(self, input_data: BookingConfirmationRequest) -> BookingConfirmationReceipt:
        self.requests.append(input_data)
        return BookingConfirmationReceipt(is_queued=IsBookingConfirmationQueued(True))


class WaitlistWorld(GrowthWorld):
    """The restaurant, its waitlist and the waitlist's use cases."""

    def __init__(self, now: datetime = DEFAULT_NOW) -> None:
        super().__init__(now)
        self.confirmations = RecordingConfirmations()
        self.version = AssistantVersionDocument(
            business_id=self.business.id,
            version_number=AssistantVersionNumber(1),
            niche_key=NicheKey.RESTAURANT,
            model_id=LlmModelId("gpt-5-mini"),
            prompt_text=SystemPromptText("Prompt"),
            tools=[AssistantToolName.CHECK_AVAILABILITY],
            languages=self.business.languages,
            default_language=self.business.default_language,
            is_voice_enabled=False,
            facts=[],
            profile_revision=Microseconds(1),
        )

    def set_waitlist(self, is_enabled: bool = True, hold_minutes: int = 30) -> None:
        now = self.clock.now_microseconds()
        self.waitlist_settings_repo.save(
            WaitlistSettingsDocument(
                id=waitlist_settings_id_of(self.business.id),
                business_id=self.business.id,
                is_enabled=is_enabled,
                hold_minutes=WaitlistHoldMinutes(hold_minutes),
                created_at=now,
                updated_at=now,
            )
        )

    def join_waitlist(self) -> JoinWaitlistUseCase:
        return JoinWaitlistUseCase(
            business_repo=self.business_repo,
            waitlist_settings_repo=self.waitlist_settings_repo,
            waitlist_entry_repo=self.waitlist_entry_repo,
            resource_repo=self.resource_repo,
            knowledge_item_repo=self.knowledge_repo,
            contact_repo=self.contact_repo,
            check_availability=self.check_availability(),
            live_events=self.live_events,
            wall_clock=self.clock.wall_clock,
        )

    def offer_freed_place(self) -> OfferFreedPlaceUseCase:
        return OfferFreedPlaceUseCase(
            business_repo=self.business_repo,
            business_profile_repo=self.profile_repo,
            waitlist_settings_repo=self.waitlist_settings_repo,
            waitlist_entry_repo=self.waitlist_entry_repo,
            booking_repo=self.booking_repo,
            resource_repo=self.resource_repo,
            lock_registry=self.lock_registry,
            delivery=WaitlistOfferDelivery(
                routing=self.routing,
                sender=self.sender,
                contact_repo=self.contact_repo,
                conversation_repo=self.conversation_repo,
                message_repo=self.message_repo,
                text_resolver=self.resolver,
                live_events=self.live_events,
                whatsapp_template=None,
            ),
            live_events=self.live_events,
            busy_times_repo=self.busy_times_repo,
            busy_time_sync=self.busy_time_sync,
            wall_clock=self.clock.wall_clock,
        )

    def answer_offer(self) -> AnswerWaitlistOfferUseCase:
        return AnswerWaitlistOfferUseCase(
            waitlist_entry_repo=self.waitlist_entry_repo,
            message_repo=self.message_repo,
            resource_repo=self.resource_repo,
            create_booking=self.create_booking(),
            send_confirmation=self.confirmations,
            job_queue=self.job_queue,
            text_resolver=self.resolver,
            live_events=self.live_events,
            wall_clock=self.clock.wall_clock,
        )

    def expire_offers(self) -> ExpireWaitlistOffersUseCase:
        return ExpireWaitlistOffersUseCase(
            waitlist_entry_repo=self.waitlist_entry_repo,
            lock_registry=self.lock_registry,
            job_queue=self.job_queue,
            live_events=self.live_events,
            wall_clock=self.clock.wall_clock,
        )

    def expire_due(self) -> JobReport:
        """One run of the minute's expiry sweep."""

        return self.expire_offers().run(
            JobTick(
                job_name=EXPIRE_WAITLIST_OFFERS_JOB,
                scheduled_at=self.clock.now_microseconds(),
            )
        )

    def join(
        self,
        guest: ContactDocument,
        conversation: ConversationDocument,
        day: str,
        time_from: str | None = None,
        time_to: str | None = None,
        party_size: int = 2,
    ) -> WaitlistJoinReceipt:
        return self.join_waitlist().run(
            JoinWaitlistCommand(
                business_id=self.business.id,
                contact_id=guest.id,
                conversation_id=conversation.id,
                contact_name=guest.name,
                source_channel=conversation.channel,
                language=guest.language or self.business.default_language,
                date=LocalDate(day),
                time_from=None if time_from is None else LocalTimeOfDay(time_from),
                time_to=None if time_to is None else LocalTimeOfDay(time_to),
                party_size=PartySize(party_size),
            )
        )

    def run_offer_jobs(self) -> list[JobReport]:
        """Every queued offer job, in order, once (the worker's part)."""

        reports: list[JobReport] = []
        while calls := [
            call
            for call in self.job_queue.calls
            if call.job_name == OFFER_FREED_PLACE_JOB
        ]:
            call = calls[0]
            self.job_queue.calls.remove(call)
            reports.append(
                self.offer_freed_place().run(
                    QueuedJobInput(
                        job_id=QueuedJobId(),
                        job_name=call.job_name,
                        payload=call.payload,
                        business_id=call.business_id,
                    )
                )
            )

        return reports

    def entry(self, entry_id: WaitlistEntryId) -> WaitlistEntryDocument:
        found = self.waitlist_entry_repo.get(self.business.id, entry_id)
        assert found is not None
        return found

    def answer(
        self,
        guest: ContactDocument,
        conversation: ConversationDocument,
        text: str,
    ) -> CustomerSignalReply | None:
        return self.answer_offer().run(self.turn(guest, conversation, text))

    def turn(
        self,
        guest: ContactDocument,
        conversation: ConversationDocument,
        text: str,
    ) -> PreparedTurn:
        language = conversation.language or self.business.default_language
        return PreparedTurn(
            business=self.business,
            version=self.version,
            contact=guest,
            conversation=conversation,
            reply_language=language,
            gate=TurnGate.ANSWER,
            is_new_conversation=False,
            is_first_reply=False,
            customer_text=MessageText(text),
            model_text=MessageText(text),
            context_line=MessageText("context"),
            tool_context=AssistantToolContext(
                business_id=self.business.id,
                business_country_code=self.business.country_code,
                contact_id=guest.id,
                conversation_id=conversation.id,
                channel=conversation.channel,
                language=language,
                available_tools=[],
            ),
            received_at=self.clock.now_microseconds(),
        )
