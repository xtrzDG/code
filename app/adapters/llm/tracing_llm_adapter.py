import json
import uuid
from collections.abc import Sequence
from typing import cast

from typed_time_provider import Microseconds, MonotonicClock, Nanoseconds, WallClock

from app.contracts.llm import LlmAdapterContract
from app.contracts.observability import LlmTraceFacilitatorContract
from app.schemas.dto.conversations import LlmRequest, LlmResponse, LlmToolResult
from app.schemas.dto.media import LlmImageInput
from app.schemas.dto.observability import LlmGenerationTrace
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.conversations.strings import LlmProviderPayload, MessageText
from app.schemas.typings.platform.booleans import IsLlmContentTraced
from app.schemas.typings.platform.constrained_integers import ElapsedMilliseconds
from app.schemas.typings.platform.strings import CorrelationId, JobErrorText

NANOSECONDS_PER_MILLISECOND: int = 1_000_000


class TracingLlmAdapter(LlmAdapterContract):
    """
    Decorator that writes every model call to the quality journal (concept:
    "Langfuse — каждый ответ модели") and otherwise behaves like the wrapped
    adapter. Tracing problems never affect the reply.
    """

    def __init__(
        self,
        inner_adapter: LlmAdapterContract,
        trace_facilitator: LlmTraceFacilitatorContract,
        wall_clock: WallClock[Microseconds],
        monotonic_clock: MonotonicClock[Nanoseconds],
        is_content_traced: IsLlmContentTraced,
    ) -> None:
        self._inner_adapter: LlmAdapterContract = inner_adapter
        self._trace_facilitator: LlmTraceFacilitatorContract = trace_facilitator
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._monotonic_clock: MonotonicClock[Nanoseconds] = monotonic_clock
        self._is_content_traced: IsLlmContentTraced = is_content_traced

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
        started_at: Microseconds = self._wall_clock.now_unix()
        started_monotonic: Nanoseconds = self._monotonic_clock.now_monotonic()
        try:
            response: LlmResponse = self._inner_adapter.complete(request)
        except ApplicationError as error:
            self._record(request, None, started_at, started_monotonic, error)
            raise

        self._record(request, response, started_at, started_monotonic, None)
        return response

    def _record(
        self,
        request: LlmRequest,
        response: LlmResponse | None,
        started_at: Microseconds,
        started_monotonic: Nanoseconds,
        error: ApplicationError | None,
    ) -> None:
        elapsed_nanoseconds: int = int(self._monotonic_clock.now_monotonic()) - int(
            started_monotonic
        )
        trace = LlmGenerationTrace(
            trace_id=CorrelationId(str(uuid.uuid4())),
            # The model that answered: the fallback when it stood in.
            model_id=(
                request.model_id
                if response is None or response.fallback_model_id is None
                else response.fallback_model_id
            ),
            effort=request.effort,
            offered_tools=[tool.name for tool in request.tools],
            called_tools=(
                []
                if response is None
                else [call.tool_name for call in response.tool_calls]
            ),
            stop_reason=None if response is None else response.stop_reason,
            input_tokens=(
                LlmTokenCount(0) if response is None else response.input_tokens
            ),
            output_tokens=(
                LlmTokenCount(0) if response is None else response.output_tokens
            ),
            started_at=started_at,
            elapsed=ElapsedMilliseconds(
                max(0, elapsed_nanoseconds // NANOSECONDS_PER_MILLISECOND)
            ),
            input_text=self._last_user_text(request),
            output_text=(
                response.text
                if self._is_content_traced and response is not None
                else None
            ),
            error=None if error is None else JobErrorText(type(error).__name__),
        )
        self._trace_facilitator.record_generation(trace)

    def _last_user_text(self, request: LlmRequest) -> MessageText | None:
        if not self._is_content_traced or not request.transcript:
            return None

        return extract_user_text(request.transcript[-1])


def extract_user_text(payload: LlmProviderPayload) -> MessageText | None:
    """Text blocks of a canonical user turn, or None for other turn shapes."""

    try:
        turn: object = json.loads(payload)
    except json.JSONDecodeError:
        return None

    if not isinstance(turn, dict):
        return None

    content: object = cast(dict[str, object], turn).get("content")
    if not isinstance(content, list):
        return None

    texts: list[str] = []
    for block in cast(list[object], content):
        if not isinstance(block, dict):
            continue

        typed_block: dict[str, object] = cast(dict[str, object], block)
        text: object = typed_block.get("text")
        if typed_block.get("type") == "text" and isinstance(text, str):
            texts.append(text)

    return MessageText("\n".join(texts)) if texts else None
