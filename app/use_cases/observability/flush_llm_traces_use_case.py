from app.contracts.observability import LlmTraceFacilitatorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.jobs import JobReport, JobTick


class FlushLlmTracesUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Periodic job: send the buffered model-call traces to the quality journal
    (Langfuse in the concept). Delivery problems are logged by the
    facilitator and never fail the job.
    """

    def __init__(self, trace_facilitator: LlmTraceFacilitatorContract) -> None:
        self._trace_facilitator: LlmTraceFacilitatorContract = trace_facilitator

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        self._trace_facilitator.flush()
        return JobReport()
