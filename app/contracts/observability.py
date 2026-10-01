"""Quality journal and error reporting seams (Langfuse and Sentry in the concept)."""

from typing import Protocol

from app.contracts.facilitator_contract import FacilitatorContract
from app.schemas.dto.observability import LlmGenerationTrace


class LlmTraceFacilitatorContract(FacilitatorContract, Protocol):
    def record_generation(self, trace: LlmGenerationTrace) -> None:
        """Queue one generation for the journal. Never raises."""
        raise NotImplementedError

    def flush(self) -> None:
        """Send everything queued so far. Never raises."""
        raise NotImplementedError


class ErrorReportingFacilitatorContract(FacilitatorContract, Protocol):
    def capture_exception(self, error: BaseException) -> None:
        """Report an unexpected error. Never raises."""
        raise NotImplementedError
