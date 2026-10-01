"""
Cost estimate of autotest calls to the AI customer and the judge.

The assistant's own replies are priced by the conversation engine (stored
on its messages); these list prices cover the extra test calls. A model
without a list price costs 0 in the estimate.
"""

from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

from app.schemas.dto.assistants import LlmTokenPrice
from app.schemas.typings.assistants.constrained_integers import (
    LlmPricePerMillionTokensMicroUsd,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount

TOKENS_PER_MILLION: Decimal = Decimal(1_000_000)
WHOLE_MICRO_USD: Decimal = Decimal(1)
# OpenAI list price of gpt-5-mini (the concept's model): $0.25 per million
# input tokens and $2.00 per million output tokens. Re-check before relying
# on the totals; override with the constructor argument of the use case.
DEFAULT_LLM_TOKEN_PRICES: tuple[LlmTokenPrice, ...] = (
    LlmTokenPrice(
        model_id=LlmModelId("gpt-5-mini"),
        input_price=LlmPricePerMillionTokensMicroUsd(250_000),
        output_price=LlmPricePerMillionTokensMicroUsd(2_000_000),
    ),
)


def estimate_llm_cost(
    prices: Sequence[LlmTokenPrice],
    model_id: LlmModelId,
    input_tokens: LlmTokenCount,
    output_tokens: LlmTokenCount,
) -> CostMicroUsd:
    """Tokens times the model's list price, rounded half up to a micro-dollar."""

    for price in prices:
        if price.model_id != model_id:
            continue

        micro_usd: Decimal = (
            Decimal(int(input_tokens)) * Decimal(int(price.input_price))
            + Decimal(int(output_tokens)) * Decimal(int(price.output_price))
        ) / TOKENS_PER_MILLION
        return CostMicroUsd(
            int(micro_usd.quantize(WHOLE_MICRO_USD, rounding=ROUND_HALF_UP))
        )

    return CostMicroUsd(0)
