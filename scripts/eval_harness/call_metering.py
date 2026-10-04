"""Cost and model latency of a scenario sample, by the role of each call."""

from collections.abc import Sequence
from enum import StrEnum

from app.contracts.llm_cassettes import LlmCallObserverContract
from app.schemas.dto.assistants.assembly_sources import LlmTokenPrice
from app.schemas.dto.conversations import LlmRequest, LlmResponse
from app.schemas.typings.platform.constrained_integers import ElapsedMilliseconds
from app.utilities.assembly.autotest_prompts import (
    CUSTOMER_PERSONA_OPENING,
    JUDGE_SYSTEM_PROMPT,
)
from app.utilities.assembly.llm_costs import DEFAULT_LLM_TOKEN_PRICES, estimate_llm_cost


class CallRole(StrEnum):
    """Who a model call speaks for in an evaluation conversation."""

    ASSISTANT = "assistant"
    CUSTOMER = "customer"
    JUDGE = "judge"


def role_of(request: LlmRequest) -> CallRole:
    prompt: str = str(request.system_prompt)
    if prompt == JUDGE_SYSTEM_PROMPT:
        return CallRole.JUDGE

    if prompt.startswith(CUSTOMER_PERSONA_OPENING):
        return CallRole.CUSTOMER

    return CallRole.ASSISTANT


class CallMeter(LlmCallObserverContract):
    """
    Adds up the list-price cost of every answered call and the model time
    of the assistant's calls (a turn's latency is the assistant time it
    added; replays report the recorded time, so reports are stable).
    """

    def __init__(
        self, prices: Sequence[LlmTokenPrice] = DEFAULT_LLM_TOKEN_PRICES
    ) -> None:
        self._prices: tuple[LlmTokenPrice, ...] = tuple(prices)
        self.cost_micro_usd: dict[CallRole, int] = {role: 0 for role in CallRole}
        self.calls: dict[CallRole, int] = {role: 0 for role in CallRole}
        self.assistant_elapsed_ms: int = 0

    def observe(
        self,
        request: LlmRequest,
        response: LlmResponse,
        elapsed: ElapsedMilliseconds,
    ) -> None:
        role: CallRole = role_of(request)
        self.calls[role] += 1
        self.cost_micro_usd[role] += int(
            estimate_llm_cost(
                self._prices,
                request.model_id,
                response.input_tokens,
                response.output_tokens,
            )
        )
        if role is CallRole.ASSISTANT:
            self.assistant_elapsed_ms += int(elapsed)

    @property
    def total_cost_micro_usd(self) -> int:
        return sum(self.cost_micro_usd.values())
