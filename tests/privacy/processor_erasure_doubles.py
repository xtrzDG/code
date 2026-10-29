"""
Fakes of the sub-processors and the job queue for the deletions of copies
at Langfuse and ElevenLabs: no network, every request recorded.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

from typed_time_provider import Microseconds

from app.adapters.privacy.elevenlabs_conversation_erasure_adapter import (
    ElevenLabsConversationErasureAdapter,
)
from app.adapters.privacy.langfuse_trace_erasure_adapter import (
    LangfuseTraceErasureAdapter,
)
from app.adapters.privacy.messaging_platform_erasure_adapter import (
    MessagingPlatformErasureAdapter,
)
from app.clients.elevenlabs.unconfigured_elevenlabs_client import (
    UnconfiguredElevenLabsClient,
)
from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.processor_erasure import (
    LangfuseTraceClientContract,
    ProcessorErasureAdapterContract,
)
from app.facilitators.privacy.processor_erasure_facilitator import (
    ProcessorErasureFacilitator,
)
from app.schemas.constants.jobs import JobLane
from app.schemas.constants.privacy import SubProcessor
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import ProviderCallId
from app.schemas.typings.platform.constrained_strings import JobName, JobSerialKey
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import (
    CorrelationId,
    JobPayloadJson,
    TraceSessionId,
)


@dataclass(frozen=True)
class QueuedJob:
    name: JobName
    payload: JobPayloadJson
    business_id: BusinessId | None
    lane: JobLane


@dataclass
class RecordingJobQueue(JobQueueFacilitatorContract):
    """The job queue as a list: what was queued, in order."""

    jobs: list[QueuedJob] = field(default_factory=list[QueuedJob])

    def enqueue(
        self,
        job_name: JobName,
        payload: JobPayloadJson,
        business_id: BusinessId | None,
        run_at: Microseconds | None = None,
        lane: JobLane = JobLane.DEFAULT,
        serial_key: JobSerialKey | None = None,
    ) -> QueuedJobId:
        del run_at, serial_key
        self.jobs.append(QueuedJob(job_name, payload, business_id, lane))
        return QueuedJobId()


@dataclass
class FakeLangfuseTraces(LangfuseTraceClientContract):
    """Langfuse's traces by session; deletions recorded; can fail first."""

    sessions: dict[str, list[str]] = field(default_factory=dict[str, list[str]])
    deleted: list[str] = field(default_factory=list[str])
    failures_left: int = 0

    def list_session_trace_ids(self, session_id: TraceSessionId) -> list[CorrelationId]:
        if self.failures_left > 0:
            self.failures_left -= 1
            raise ExternalServiceError("Langfuse traces request returned HTTP 503.")

        return [
            CorrelationId(trace_id)
            for trace_id in self.sessions.get(str(session_id), [])
            if trace_id not in self.deleted
        ]

    def delete_traces(self, trace_ids: Sequence[CorrelationId]) -> None:
        self.deleted.extend(str(trace_id) for trace_id in trace_ids)


class RecordingElevenLabsClient(UnconfiguredElevenLabsClient):
    """ElevenLabs that only deletes conversations (and records which)."""

    def __init__(self) -> None:
        self.deleted: list[str] = []

    def delete_conversation(self, conversation_id: ProviderCallId) -> None:
        self.deleted.append(str(conversation_id))


@dataclass
class ProcessorErasureBed:
    """The real facilitator over fake processors and a recording queue."""

    job_queue: RecordingJobQueue = field(default_factory=RecordingJobQueue)
    langfuse: FakeLangfuseTraces = field(default_factory=FakeLangfuseTraces)
    elevenlabs: RecordingElevenLabsClient = field(
        default_factory=RecordingElevenLabsClient
    )

    def facilitator(self) -> ProcessorErasureFacilitator:
        adapters: list[ProcessorErasureAdapterContract] = [
            LangfuseTraceErasureAdapter(self.langfuse),
            ElevenLabsConversationErasureAdapter(self.elevenlabs),
            MessagingPlatformErasureAdapter(SubProcessor.META),
            MessagingPlatformErasureAdapter(SubProcessor.TELEGRAM),
        ]
        return ProcessorErasureFacilitator(adapters=adapters, job_queue=self.job_queue)
