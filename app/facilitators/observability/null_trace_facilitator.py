from app.contracts.observability import LlmTraceFacilitatorContract
from app.schemas.dto.observability import LlmGenerationTrace


class NullTraceFacilitator(LlmTraceFacilitatorContract):
    """Used when Langfuse keys are not configured: traces are discarded."""

    def record_generation(self, trace: LlmGenerationTrace) -> None:
        del trace

    def flush(self) -> None:
        return None
