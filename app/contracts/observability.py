"""
Quality journal, error reporting and job monitoring seams (Langfuse and
Sentry in the concept).
"""

from typing import Protocol

from app.contracts.facilitator_contract import FacilitatorContract
from app.schemas.constants.observability import PeriodicJobOutcome
from app.schemas.dto.observability import JobCheckIn, LlmGenerationTrace
from app.schemas.dto.widget_errors import WidgetErrorReport
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName


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


class ClientErrorReportingFacilitatorContract(FacilitatorContract, Protocol):
    def capture_widget_error(self, report: WidgetErrorReport) -> None:
        """Report an error of the website widget (no texts). Never raises."""
        raise NotImplementedError


class JobMonitorFacilitatorContract(FacilitatorContract, Protocol):
    """
    Check-ins of periodic jobs (Sentry Crons): a job that stops running on
    time, runs too long or fails shows up as a missed or failed check-in.
    """

    def job_started(
        self,
        job_name: JobName,
        interval_seconds: JobIntervalSeconds,
    ) -> JobCheckIn:
        """Tell the monitor a run started. Never raises."""
        raise NotImplementedError

    def job_finished(self, check_in: JobCheckIn, outcome: PeriodicJobOutcome) -> None:
        """Tell the monitor how the run ended. Never raises."""
        raise NotImplementedError
