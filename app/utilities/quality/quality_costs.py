"""
What judging one real conversation may cost, before the call, and what it
did cost, after it: list prices per million tokens (llm_costs.py). A judge
model without a list price is priced as the dearest known model, so the
nightly budget holds whatever LLM_JUDGE_MODEL_ID says.
"""

from collections.abc import Sequence

from app.schemas.dto.assistants.assembly_sources import LlmTokenPrice
from app.schemas.typings.assistants.constrained_integers import LlmMaxOutputTokens
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount

TOKENS_PER_MILLION: int = 1_000_000
# A token is at least about three characters in the languages served
# (fewer characters per token would only overestimate).
CHARACTERS_PER_TOKEN: int = 3


def price_of(prices: Sequence[LlmTokenPrice], model_id: LlmModelId) -> LlmTokenPrice:
    """The model's list price; the dearest known one for an unknown model."""

    for price in prices:
        if price.model_id == model_id:
            return price

    return max(
        prices, key=lambda price: (int(price.output_price), int(price.input_price))
    )


def cost_of(
    price: LlmTokenPrice, input_tokens: LlmTokenCount, output_tokens: LlmTokenCount
) -> CostMicroUsd:
    """Tokens times the list price, rounded up to a whole micro-dollar."""

    micro_usd_millions: int = int(input_tokens) * int(price.input_price) + int(
        output_tokens
    ) * int(price.output_price)
    return CostMicroUsd(-(-micro_usd_millions // TOKENS_PER_MILLION))


def worst_case_cost(
    price: LlmTokenPrice, request_text: str, max_output_tokens: LlmMaxOutputTokens
) -> CostMicroUsd:
    """The most a request of this text can cost: every output token used."""

    return cost_of(
        price,
        LlmTokenCount(len(request_text) // CHARACTERS_PER_TOKEN + 1),
        LlmTokenCount(int(max_output_tokens)),
    )
