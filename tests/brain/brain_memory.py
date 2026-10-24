"""
The customer memory of a brain test world: its settings, the bookings,
requests, resources and notes it reads (real repositories over in-memory
collections), and a job queue that keeps the summary jobs it queues.
"""

from dataclasses import dataclass, field

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.jobs import JobQueueFacilitatorContract
from app.repositories.assistant_settings_repository import (
    AssistantSettingsRepository,
)
from app.repositories.booking_repositories import BookingRepository, LeadRepository
from app.repositories.inbox_repositories import ConversationNoteRepository
from app.repositories.knowledge_repositories import ResourceRepository
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.assistant_settings import AssistantSettingsDocument
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.conversation_notes import ConversationNoteDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import JobName, JobSerialKey
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson


@dataclass(frozen=True)
class ScheduledJob:
    name: JobName
    payload: JobPayloadJson
    business_id: BusinessId | None
    run_at: Microseconds | None
    lane: JobLane


@dataclass
class ScheduledJobs(JobQueueFacilitatorContract):
    """Keeps every job queued, with when it is due."""

    jobs: list[ScheduledJob] = field(default_factory=list[ScheduledJob])

    def enqueue(
        self,
        job_name: JobName,
        payload: JobPayloadJson,
        business_id: BusinessId | None,
        run_at: Microseconds | None = None,
        lane: JobLane = JobLane.DEFAULT,
        serial_key: JobSerialKey | None = None,
    ) -> QueuedJobId:
        del serial_key
        self.jobs.append(ScheduledJob(job_name, payload, business_id, run_at, lane))
        return QueuedJobId()


@dataclass(frozen=True)
class BrainMemory:
    settings_repo: AssistantSettingsRepository
    booking_repo: BookingRepository
    lead_repo: LeadRepository
    resource_repo: ResourceRepository
    note_repo: ConversationNoteRepository
    jobs: ScheduledJobs


def build_brain_memory() -> BrainMemory:
    return BrainMemory(
        settings_repo=AssistantSettingsRepository(
            InMemoryDocumentCollectionAdapter(AssistantSettingsDocument)
        ),
        booking_repo=BookingRepository(
            InMemoryDocumentCollectionAdapter(BookingDocument)
        ),
        lead_repo=LeadRepository(InMemoryDocumentCollectionAdapter(LeadDocument)),
        resource_repo=ResourceRepository(
            InMemoryDocumentCollectionAdapter(ResourceDocument)
        ),
        note_repo=ConversationNoteRepository(
            InMemoryDocumentCollectionAdapter(ConversationNoteDocument)
        ),
        jobs=ScheduledJobs(),
    )
