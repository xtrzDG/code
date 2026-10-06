from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.assistants import LlmProvider
from app.schemas.constants.telemetry import LlmCallOutcome
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
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
