"""A job queue for tests: it keeps what the use cases enqueue."""

from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.contracts.jobs import JobQueueFacilitatorContract
from app.schemas.constants.jobs import JobLane
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import JobName, JobSerialKey
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson


@dataclass(frozen=True)
class QueuedJob:
    job_id: QueuedJobId
    name: JobName
    payload: JobPayloadJson
    business_id: BusinessId | None
    lane: JobLane
    serial_key: JobSerialKey | None


class RecordingJobQueue(JobQueueFacilitatorContract):
    def __init__(self) -> None:
        self.jobs: list[QueuedJob] = []

    def enqueue(
        self,
        job_name: JobName,
        payload: JobPayloadJson,
        business_id: BusinessId | None,
        run_at: Microseconds | None = None,
        lane: JobLane = JobLane.DEFAULT,
        serial_key: JobSerialKey | None = None,
    ) -> QueuedJobId:
        del run_at
        job_id = QueuedJobId()
        self.jobs.append(
            QueuedJob(job_id, job_name, payload, business_id, lane, serial_key)
        )
        return job_id
