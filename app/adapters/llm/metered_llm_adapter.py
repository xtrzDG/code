from collections.abc import Generator, Sequence
from contextlib import contextmanager

from typed_time_provider import MonotonicClock, Nanoseconds

from app.contracts.llm import LlmAdapterContract
from app.contracts.service_metrics import ServiceMetricsContract
from app.schemas.constants.assistants import LlmProvider
from app.schemas.constants.telemetry import LlmCallOutcome, SpanKind
from app.schemas.dto.conversations import LlmRequest, LlmResponse, LlmToolResult
from app.schemas.dto.media import LlmImageInput
from app.schemas.dto.telemetry import LlmCallObservation
from app.schemas.exceptions.application_errors import LlmRefusedError
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.conversations.strings import LlmProviderPayload, MessageText
from app.utilities.conversations.llm_models import resolve_llm_provider
from app.utilities.observability.metrics.observed_durations import observed_seconds
from app.utilities.observability.tracing.span_tracer import (
    SpanHandle,
    SpanTracer,
)

NANOSECONDS_PER_SECOND: float = 1_000_000_000.0
LLM_SPAN_OPERATION: str = "gen_ai.chat"


class MeteredLlmAdapter(LlmAdapterContract):
    """
    Decorator that measures every model call for /metrics (time, outcome,
    tokens by provider and model: the model that answered, a fallback when
    one stood in) and wraps it in a client span. A refusal is the model's
    answer, not an error. Otherwise it behaves like the wrapped adapter;
    measuring never fails a call.
    """

    def __init__(
        self,
        inner_adapter: LlmAdapterContract,
        metrics: ServiceMetricsContract,
        tracer: SpanTracer,
        monotonic_clock: MonotonicClock[Nanoseconds],
    ) -> None:
        self._inner_adapter: LlmAdapterContract = inner_adapter
        self._metrics: ServiceMetricsContract = metrics
        self._tracer: SpanTracer = tracer
        self._monotonic_clock: MonotonicClock[Nanoseconds] = monotonic_clock

    def build_user_text_turn(self, text: MessageText) -> LlmProviderPayload:
        return self._inner_adapter.build_user_text_turn(text)

    def build_user_media_turn(
        self,
        text: MessageText,
        images: Sequence[LlmImageInput],
    ) -> LlmProviderPayload:
        return self._inner_adapter.build_user_media_turn(text, images)

    def build_tool_results_turn(
        self,
        results: list[LlmToolResult],
    ) -> LlmProviderPayload:
        return self._inner_adapter.build_tool_results_turn(results)

    def complete(self, request: LlmRequest) -> LlmResponse:
        started: int = int(self._monotonic_clock.now_monotonic())
        with self._span(request) as span:
            try:
                response: LlmResponse = self._inner_adapter.complete(request)
            except LlmRefusedError:
                self._observe(request.model_id, LlmCallOutcome.REFUSED, started)
                raise
            except Exception:
                self._observe(request.model_id, LlmCallOutcome.ERROR, started)
                raise

            answered_by: LlmModelId = response.fallback_model_id or request.model_id
            self._observe(answered_by, LlmCallOutcome.OK, started, response)
            span.set_attribute("gen_ai.response.model", str(answered_by))
            span.set_attribute("gen_ai.usage.input_tokens", int(response.input_tokens))
            span.set_attribute(
                "gen_ai.usage.output_tokens", int(response.output_tokens)
            )
            return response

    @contextmanager
    def _span(self, request: LlmRequest) -> Generator[SpanHandle]:
        provider: LlmProvider | None = resolve_llm_provider(request.model_id)
        with self._tracer.span(
            f"chat {request.model_id}",
            SpanKind.CLIENT,
            {
                "gen_ai.operation.name": "chat",
                "gen_ai.system": "unknown" if provider is None else provider.value,
                "gen_ai.request.model": str(request.model_id),
                "sentry.op": LLM_SPAN_OPERATION,
            },
        ) as span:
            yield span

    def _observe(
        self,
        model_id: LlmModelId,
        outcome: LlmCallOutcome,
        started: int,
        response: LlmResponse | None = None,
    ) -> None:
        provider: LlmProvider | None = resolve_llm_provider(model_id)
        if provider is None:
            return

        elapsed: int = int(self._monotonic_clock.now_monotonic()) - started
        self._metrics.observe_llm_call(
            LlmCallObservation(
                provider=provider,
                model_id=model_id,
                outcome=outcome,
                duration=observed_seconds(elapsed / NANOSECONDS_PER_SECOND),
                input_tokens=(
                    LlmTokenCount(0) if response is None else response.input_tokens
                ),
                output_tokens=(
                    LlmTokenCount(0) if response is None else response.output_tokens
                ),
            )
        )
