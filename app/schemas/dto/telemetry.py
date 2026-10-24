from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.assistants import LlmProvider
from app.schemas.constants.jobs import JobLane
from app.schemas.constants.telemetry import LlmCallOutcome
from app.schemas.dto.admin_system import DeadJobTally
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.monitoring.constrained_integers import (
    LaneJobCount,
    WaitSeconds,
)
from app.schemas.typings.observability.constrained_floats import ObservedSeconds
from app.schemas.typings.observability.constrained_integers import HttpStatusCode
from app.schemas.typings.observability.constrained_strings import MetricsLabel


class HttpRequestObservation(ImmutableDTO):
    """
    One answered HTTP request as the metrics see it: the method, the route
    template (never the path with its ids), the status and how long it took.
    """

    method: MetricsLabel
    route: MetricsLabel
    status_code: HttpStatusCode
    duration: ObservedSeconds


class LlmCallObservation(ImmutableDTO):
    """One language-model call: who answered, how it ended, time and tokens."""

    provider: LlmProvider
    model_id: LlmModelId
    outcome: LlmCallOutcome
    duration: ObservedSeconds
    input_tokens: LlmTokenCount = LlmTokenCount(0)
    output_tokens: LlmTokenCount = LlmTokenCount(0)


class JobQueueQuery(ImmutableDTO):
    """Ask for the job queue's depth and dead letters (a metrics scrape)."""


class LaneDepth(ImmutableDTO):
    """One lane: the jobs due now and how long the oldest of them has waited."""

    lane: JobLane
    due_jobs: LaneJobCount
    oldest_wait_seconds: WaitSeconds | None = None


class JobQueueMeasurement(ImmutableDTO):
    """The queue as a scrape sees it: every lane, and dead letters by job."""

    lanes: list[LaneDepth] = Field(default_factory=list[LaneDepth])
    dead_jobs: list[DeadJobTally] = Field(default_factory=list[DeadJobTally])
