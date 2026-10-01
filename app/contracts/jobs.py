"""Background work: the durable queue and job handlers."""

from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.facilitator_contract import FacilitatorContract
from app.contracts.operator_contract import OperatorContract
from app.contracts.repo_contract import RepoContract
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.dto.jobs import JobReport, JobTick, QueuedJobInput
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson

type PeriodicJobOperator = OperatorContract[JobTick, JobReport]
type QueuedJobOperator = OperatorContract[QueuedJobInput, JobReport]


class QueuedJobRepoContract(RepoContract, Protocol):
    def save(self, job: QueuedJobDocument) -> None:
        raise NotImplementedError

    def get(self, job_id: QueuedJobId) -> QueuedJobDocument | None:
        raise NotImplementedError

    def list_due(self, now: Microseconds) -> list[QueuedJobDocument]:
        """Pending jobs with run_at <= now, oldest first."""
        raise NotImplementedError


class JobQueueFacilitatorContract(FacilitatorContract, Protocol):
    def enqueue(
        self,
        job_name: JobName,
        payload: JobPayloadJson,
        business_id: BusinessId | None,
        run_at: Microseconds | None = None,
    ) -> QueuedJobId:
        """Queue a job to run at `run_at` (now when omitted)."""
        raise NotImplementedError
