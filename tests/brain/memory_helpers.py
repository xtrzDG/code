"""Builders for customer memory tests: bookings, notes, running summary jobs."""

from datetime import UTC, datetime

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.schemas.constants.bookings import BookingStatus, ResourceKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversation_notes import ConversationNoteDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
    ResourceCapacity,
)
from app.schemas.typings.bookings.strings import ResourceName
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.inbox.constrained_strings import ConversationNoteText
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.use_cases.conversations.memory.summarize_conversation_use_case import (
    SummarizeConversationUseCase,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.memory.summary_jobs import SUMMARIZE_CONVERSATION_JOB
from tests.brain.brain_memory import ScheduledJob
from tests.brain.brain_world import BrainWorld

SUMMARY_MODEL: str = "gpt-5-nano"


def only_contact(world: BrainWorld) -> ContactDocument:
    contacts: list[ContactDocument] = world.contacts()
    assert len(contacts) == 1
    return contacts[0]


def add_booking(
    world: BrainWorld,
    contact: ContactDocument,
    starts: datetime,
    *,
    status: BookingStatus = BookingStatus.CONFIRMED,
    is_sandbox: bool = False,
    party_size: int = 4,
) -> BookingDocument:
    """A booking of "Table 4" for two hours from `starts` (an aware time)."""

    resource = ResourceDocument(
        business_id=world.business.id,
        kind=ResourceKind.TABLE,
        name=ResourceName("Table 4"),
        capacity=ResourceCapacity(6),
    )
    world.memory.resource_repo.save(resource)
    starts_at: int = int(starts.astimezone(UTC).timestamp())
    booking = BookingDocument(
        business_id=world.business.id,
        resource_id=resource.id,
        contact_id=contact.id,
        starts_at=BookingStartsAtUnixSeconds(starts_at),
        ends_at=BookingEndsAtUnixSeconds(starts_at + 2 * 3600),
        party_size=PartySize(party_size),
        status=status,
        source_channel=ChannelKind.WHATSAPP,
        is_sandbox=is_sandbox,
    )
    world.memory.booking_repo.save(booking)
    return booking


def add_note(world: BrainWorld, conversation_id: ConversationId, text: str) -> None:
    world.memory.note_repo.add(
        ConversationNoteDocument(
            business_id=world.business.id,
            conversation_id=conversation_id,
            author_user_id=world.owner_id,
            text=ConversationNoteText(text),
        )
    )


def summary_jobs(world: BrainWorld) -> list[ScheduledJob]:
    return [
        job for job in world.memory.jobs.jobs if job.name == SUMMARIZE_CONVERSATION_JOB
    ]


def build_summarizer(
    world: BrainWorld, llm: ScriptedLlmAdapter
) -> SummarizeConversationUseCase:
    return SummarizeConversationUseCase(
        business_repo=world.business_repo,
        conversation_repo=world.conversation_repo,
        conversation_memory_repo=world.conversation_repo,
        contact_repo=world.contact_repo,
        message_repo=world.message_repo,
        assistant_settings_repo=world.memory.settings_repo,
        job_queue=world.memory.jobs,
        llm_adapter=llm,
        app_settings=assemble_app_settings({"LLM_SUMMARY_MODEL_ID": SUMMARY_MODEL}),
        wall_clock=world.clock.wall_clock(),
    )


def run_summary_job(
    summarizer: SummarizeConversationUseCase,
    job: ScheduledJob,
    *,
    is_final_attempt: bool = False,
) -> JobReport:
    return summarizer.run(
        QueuedJobInput(
            job_id=QueuedJobId(),
            job_name=job.name,
            payload=job.payload,
            business_id=job.business_id,
            is_final_attempt=is_final_attempt,
        )
    )
