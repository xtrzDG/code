"""
Which provider serves a model id, and what a model call costs.

Prices are list prices in USD per one million tokens (OpenAI gpt-5-mini as
in the concept; Anthropic models from the provider price list). One USD per
million tokens is exactly one micro-USD per token, so a price is also the
micro-USD cost of one token.
"""

import logging
import re
from decimal import ROUND_HALF_UP, Decimal
from typing import NamedTuple

from app.schemas.constants.assistants import LlmProvider
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount

LOGGER: logging.Logger = logging.getLogger(__name__)
OPENAI_MODEL_PATTERN: re.Pattern[str] = re.compile(r"^(gpt-|o[0-9])")
ANTHROPIC_MODEL_PREFIX: str = "claude-"
SCRIPTED_MODEL_ID: str = "scripted"
WHOLE_MICRO_USD: Decimal = Decimal(1)


class LlmTokenPrice(NamedTuple):
    """USD per one million input and output tokens (technical price record)."""

    input_usd_per_million: Decimal
    output_usd_per_million: Decimal


class LlmCallCost(NamedTuple):
    """Cost of one model call split by direction."""

    input_cost: CostMicroUsd
    output_cost: CostMicroUsd

    @property
    def total(self) -> CostMicroUsd:
        return CostMicroUsd(int(self.input_cost) + int(self.output_cost))


LLM_TOKEN_PRICES: dict[str, LlmTokenPrice] = {
    "gpt-5-mini": LlmTokenPrice(Decimal("0.25"), Decimal("2.00")),
    "claude-opus-5-5": LlmTokenPrice(Decimal("4.00"), Decimal("20.00")),
    "claude-sonnet-5-5": LlmTokenPrice(Decimal("2.00"), Decimal("10.00")),
    "claude-haiku-4-5": LlmTokenPrice(Decimal("1.00"), Decimal("5.00")),
    SCRIPTED_MODEL_ID: LlmTokenPrice(Decimal(0), Decimal(0)),
}


def resolve_llm_provider(model_id: LlmModelId) -> LlmProvider | None:
    """
    Provider of a model id: "gpt-*" and "o<digit>*" are OpenAI, "claude-*"
    Anthropic, "scripted" the offline test model; None for anything else.
    """

    model_text: str = str(model_id)
    if model_text == SCRIPTED_MODEL_ID:
        return LlmProvider.SCRIPTED

    if model_text.startswith(ANTHROPIC_MODEL_PREFIX):
        return LlmProvider.ANTHROPIC

    if OPENAI_MODEL_PATTERN.match(model_text) is not None:
        return LlmProvider.OPENAI

    return None


def find_llm_token_price(model_id: LlmModelId) -> LlmTokenPrice | None:
    """
    Price of a model id; dated snapshots ("gpt-5-mini-2025-08-07") use the
    price of their longest known prefix.
    """

    model_text: str = str(model_id)
    exact_price: LlmTokenPrice | None = LLM_TOKEN_PRICES.get(model_text)
    if exact_price is not None:
        return exact_price

    for known_model in sorted(LLM_TOKEN_PRICES, key=len, reverse=True):
        if model_text.startswith(f"{known_model}-"):
            return LLM_TOKEN_PRICES[known_model]

    return None


def compute_llm_call_cost(
    model_id: LlmModelId,
    input_tokens: LlmTokenCount,
    output_tokens: LlmTokenCount,
) -> LlmCallCost:
    """
    Cost in micro-USD, rounded half up per direction. Unknown models cost 0
    and log a warning so the price table can be completed.
    """

    price: LlmTokenPrice | None = find_llm_token_price(model_id)
    if price is None:
        LOGGER.warning("No token price for model %s; cost recorded as 0.", model_id)
        return LlmCallCost(CostMicroUsd(0), CostMicroUsd(0))

    return LlmCallCost(
        input_cost=price_tokens(int(input_tokens), price.input_usd_per_million),
        output_cost=price_tokens(int(output_tokens), price.output_usd_per_million),
    )


def price_tokens(token_count: int, usd_per_million: Decimal) -> CostMicroUsd:
    micro_usd: Decimal = (Decimal(token_count) * usd_per_million).quantize(
        WHOLE_MICRO_USD,
        rounding=ROUND_HALF_UP,
    )
    return CostMicroUsd(int(micro_usd))
