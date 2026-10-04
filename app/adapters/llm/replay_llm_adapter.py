from app.adapters.llm.llm_payloads import (
    build_tool_results_payload,
    build_user_text_payload,
)
from app.contracts.llm import LlmAdapterContract
from app.contracts.llm_cassettes import (
    LlmCallObserverContract,
    LlmCassetteStoreAdapterContract,
)
from app.schemas.dto.conversations import LlmRequest, LlmResponse, LlmToolResult
from app.schemas.dto.llm_cassettes import (
    LlmCassetteEntry,
    LlmCassetteMiss,
    LlmCassetteRequest,
    LlmCassetteTake,
)
from app.schemas.exceptions.evaluation_errors import LlmCassetteMissError
from app.schemas.typings.conversations.strings import LlmProviderPayload, MessageText
from app.schemas.typings.evaluations.constrained_integers import (
    LlmCassetteSampleIndex,
)
from app.schemas.typings.evaluations.strings import LlmCassetteMissReason
from app.utilities.llm_cassettes.cassette_keys import build_cassette_request
from app.utilities.llm_cassettes.cassette_misses import explain_cassette_miss


class ReplayLlmAdapter(LlmAdapterContract):
    """
    The evaluation harness's model without a provider: every request is
    answered with what was recorded for the same request (model,
    instruction, tools and canonical transcript) in sample `sample_index`.

    A request without a recording raises `LlmCassetteMissError`, which the
    conversation engine handles like an unavailable provider; the miss and
    its reason (an instruction diff, the tools that changed, the turn where
    the conversation went another way) stay in `misses`, so the harness
    flags the cassette instead of scoring a conversation that never
    happened. User and tool result turns are canonical, as for every
    provider.
    """

    def __init__(
        self,
        cassette_store: LlmCassetteStoreAdapterContract,
        sample_index: LlmCassetteSampleIndex,
        call_observer: LlmCallObserverContract | None = None,
    ) -> None:
        self._cassette_store: LlmCassetteStoreAdapterContract = cassette_store
        self._sample_index: LlmCassetteSampleIndex = sample_index
        self._call_observer: LlmCallObserverContract | None = call_observer
        self.misses: list[LlmCassetteMiss] = []

    def build_user_text_turn(self, text: MessageText) -> LlmProviderPayload:
        return build_user_text_payload(text)

    def build_tool_results_turn(
        self,
        results: list[LlmToolResult],
    ) -> LlmProviderPayload:
        return build_tool_results_payload(results)

    def complete(self, request: LlmRequest) -> LlmResponse:
        cassette_request: LlmCassetteRequest = build_cassette_request(request)
        entry: LlmCassetteEntry | None = self._cassette_store.find(cassette_request.key)
        take: LlmCassetteTake | None = (
            None
            if entry is None
            else next(
                (
                    candidate
                    for candidate in entry.takes
                    if candidate.sample_index == self._sample_index
                ),
                None,
            )
        )
        if take is None:
            reason: LlmCassetteMissReason = self._explain(request, cassette_request)
            self.misses.append(
                LlmCassetteMiss(
                    request=cassette_request,
                    sample_index=self._sample_index,
                    reason=reason,
                )
            )
            raise LlmCassetteMissError(str(reason))

        if self._call_observer is not None:
            self._call_observer.observe(request, take.response, take.elapsed)

        return take.response

    def _explain(
        self,
        request: LlmRequest,
        cassette_request: LlmCassetteRequest,
    ) -> LlmCassetteMissReason:
        if self._cassette_store.find(cassette_request.key) is not None:
            return LlmCassetteMissReason(
                f"The request was recorded, but not for sample "
                f"{int(self._sample_index) + 1}: record more samples."
            )

        return explain_cassette_miss(
            cassette_request,
            request.system_prompt,
            [tool.name for tool in request.tools],
            self._cassette_store.list_entries(),
            self._cassette_store.read_instruction,
            self._cassette_store.read_tools,
        )
