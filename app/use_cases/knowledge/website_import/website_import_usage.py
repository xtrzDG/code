"""What reading a website costs, recorded as the business's usage."""

from typed_time_provider import Microseconds

from app.contracts.repositories.billing_repositories import UsageEventRepoContract
from app.schemas.constants.billing import UsageKind
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.dto.website_import import WebsitePageExtraction
from app.schemas.typings.billing.constrained_integers import (
    CostMicroUsd,
    UsageQuantity,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.conversations.llm_models import LlmCallCost, compute_llm_call_cost


def record_reading_usage(
    usage_event_repo: UsageEventRepoContract,
    business_id: BusinessId,
    extraction: WebsitePageExtraction,
    now: Microseconds,
) -> CostMicroUsd:
    """
    The tokens of one page's model call as usage events (input and output,
    each with its cost at the model's list price, outside any
    conversation); the call's whole cost.
    """

    cost: LlmCallCost = compute_llm_call_cost(
        extraction.model_id, extraction.input_tokens, extraction.output_tokens
    )
    usages: list[tuple[UsageKind, int, CostMicroUsd]] = [
        (UsageKind.LLM_INPUT_TOKENS, int(extraction.input_tokens), cost.input_cost),
        (UsageKind.LLM_OUTPUT_TOKENS, int(extraction.output_tokens), cost.output_cost),
    ]
    for kind, quantity, usage_cost in usages:
        if quantity == 0:
            continue

        usage_event_repo.append(
            UsageEventDocument(
                business_id=business_id,
                kind=kind,
                quantity=UsageQuantity(quantity),
                cost_micro_usd=usage_cost,
                occurred_at=now,
                created_at=now,
                updated_at=now,
            )
        )

    return CostMicroUsd(int(cost.input_cost) + int(cost.output_cost))
