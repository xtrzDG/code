from typed_time_provider import MonotonicClock, Nanoseconds

from app.contracts.llm import LlmAdapterContract
from app.contracts.llm_cassettes import (
    LlmCallObserverContract,
    LlmCassetteStoreAdapterContract,
)
from app.schemas.dto.conversations import LlmRequest, LlmResponse, LlmToolResult
from app.schemas.dto.llm_cassettes import LlmCassetteRequest, LlmCassetteTake
from app.schemas.typings.conversations.strings import LlmProviderPayload, MessageText
from app.schemas.typings.evaluations.constrained_integers import (
    LlmCassetteSampleIndex,
)
from app.schemas.typings.platform.constrained_integers import ElapsedMilliseconds
from app.utilities.llm_cassettes.cassette_keys import build_cassette_request

NANOSECONDS_PER_MILLISECOND: int = 1_000_000


class RecordingLlmAdapter(LlmAdapterContract):
    """
    Decorator of the evaluation harness: every answered model call is
    stored in the cassette under the digest of its request (model,
    instruction, tools and canonical transcript), with how long it took,
    for sample `sample_index` of its scenario. Instructions and tool names
    are kept too, so a later replay can show what changed. Failed calls
    are not recorded; the error reaches the caller unchanged.
    """

    def __init__(
        self,
        inner_adapter: LlmAdapterContract,
        cassette_store: LlmCassetteStoreAdapterContract,
        sample_index: LlmCassetteSampleIndex,
        monotonic_clock: MonotonicClock[Nanoseconds],
        call_observer: LlmCallObserverContract | None = None,
    ) -> None:
        self._inner_adapter: LlmAdapterContract = inner_adapter
        self._cassette_store: LlmCassetteStoreAdapterContract = cassette_store
        self._sample_index: LlmCassetteSampleIndex = sample_index
        self._monotonic_clock: MonotonicClock[Nanoseconds] = monotonic_clock
        self._call_observer: LlmCallObserverContract | None = call_observer

    def build_user_text_turn(self, text: MessageText) -> LlmProviderPayload:
        return self._inner_adapter.build_user_text_turn(text)

    def build_tool_results_turn(
        self,
        results: list[LlmToolResult],
    ) -> LlmProviderPayload:
        return self._inner_adapter.build_tool_results_turn(results)

    def complete(self, request: LlmRequest) -> LlmResponse:
        started: Nanoseconds = self._monotonic_clock.now_monotonic()
        response: LlmResponse = self._inner_adapter.complete(request)
        elapsed = ElapsedMilliseconds(
            max(
                0,
                (int(self._monotonic_clock.now_monotonic()) - int(started))
                // NANOSECONDS_PER_MILLISECOND,
            )
        )
        cassette_request: LlmCassetteRequest = build_cassette_request(request)
        self._cassette_store.remember_instruction(
            cassette_request.instruction_digest, request.system_prompt
        )
        self._cassette_store.remember_tools(
            cassette_request.tools_digest, [tool.name for tool in request.tools]
        )
        self._cassette_store.record(
            cassette_request,
            LlmCassetteTake(
                sample_index=self._sample_index, response=response, elapsed=elapsed
            ),
        )
        if self._call_observer is not None:
            self._call_observer.observe(request, response, elapsed)

        return response
