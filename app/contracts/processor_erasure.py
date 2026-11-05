"""
Deleting the copies of customer data the sub-processors keep, when the
platform deletes its own (an erasure, the retention purge).
"""

from collections.abc import Sequence
from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.contracts.client_contract import ClientContract
from app.contracts.facilitator_contract import FacilitatorContract
from app.schemas.constants.privacy import SubProcessor
from app.schemas.dto.processor_erasure import ProcessorErasureScope
from app.schemas.typings.compliance.constrained_integers import ErasedRecordCount
from app.schemas.typings.platform.strings import CorrelationId, TraceSessionId
from app.schemas.typings.privacy.constrained_integers import ProcessorErasureJobCount


class ProcessorErasureAdapterContract(AdapterContract, Protocol):
    """One sub-processor's side of a deletion."""

    @property
    def processor(self) -> SubProcessor:
        raise NotImplementedError

    @property
    def deletes_copies(self) -> bool:
        """False for a processor whose copies cannot be deleted (documented)."""
        raise NotImplementedError

    def copies_in(self, scope: ProcessorErasureScope) -> ProcessorErasureScope | None:
        """The part of `scope` this processor keeps copies of; None: nothing."""
        raise NotImplementedError

    def erase(self, scope: ProcessorErasureScope) -> ErasedRecordCount:
        """
        Delete this processor's copies of `scope`; how many it deleted.
        Deleting what is gone already is not an error. Raises
        ExternalServiceError when the processor fails (the job retries).
        """
        raise NotImplementedError


class ProcessorErasureFacilitatorContract(FacilitatorContract, Protocol):
    def request_erasure(self, scope: ProcessorErasureScope) -> ProcessorErasureJobCount:
        """
        Queue the deletion at every sub-processor that keeps copies of
        `scope` (a job with retries per processor and batch); how many jobs.
        """
        raise NotImplementedError

    def erase(
        self, processor: SubProcessor, scope: ProcessorErasureScope
    ) -> ErasedRecordCount:
        """Run one queued deletion at `processor` (see the adapter)."""
        raise NotImplementedError

    def erasure_processors(self) -> list[SubProcessor]:
        """The sub-processors this platform deletes copies at."""
        raise NotImplementedError


class LangfuseTraceClientContract(ClientContract, Protocol):
    """The trace endpoints of the Langfuse public API."""

    def list_session_trace_ids(self, session_id: TraceSessionId) -> list[CorrelationId]:
        """Every trace of the session (all pages)."""
        raise NotImplementedError

    def delete_traces(self, trace_ids: Sequence[CorrelationId]) -> None:
        """Delete these traces (Langfuse deletes them in the background)."""
        raise NotImplementedError
