"""
Cost estimate of autotest calls to the AI customer and the judge.

The assistant's own replies are priced by the conversation engine (stored
on its messages); these list prices cover the extra test calls. A model
without a list price costs 0 in the estimate.
"""

from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

from app.schemas.dto.assistants.assembly_sources import LlmTokenPrice
from app.schemas.typings.assistants.constrained_integers import (
    LlmPricePerMillionTokensMicroUsd,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.utilities.conversations.llm_models import LLM_TOKEN_PRICES

TOKENS_PER_MILLION: Decimal = Decimal(1_000_000)
MICRO_USD_PER_USD: Decimal = Decimal(1_000_000)
WHOLE_MICRO_USD: Decimal = Decimal(1)
# The list prices of every model the platform knows (llm_models.py: OpenAI
# gpt-5-mini of the concept, the Anthropic models a judge on the other
# provider uses). Re-check before relying on the totals; override with the
# constructor argument of the use case.
DEFAULT_LLM_TOKEN_PRICES: tuple[LlmTokenPrice, ...] = tuple(
    LlmTokenPrice(
        model_id=LlmModelId(model_id),
        input_price=LlmPricePerMillionTokensMicroUsd(
            int(price.input_usd_per_million * MICRO_USD_PER_USD)
        ),
        output_price=LlmPricePerMillionTokensMicroUsd(
            int(price.output_usd_per_million * MICRO_USD_PER_USD)
        ),
    )
    for model_id, price in LLM_TOKEN_PRICES.items()
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
