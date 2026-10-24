"""
Usage events of one reply: the reply model's tokens, the claim check's
verifier tokens (priced by the verifier's own model) and one dialog per
new real conversation.
"""

from typed_time_provider import Microseconds

from app.contracts.repositories.billing_repositories import UsageEventRepoContract
from app.schemas.constants.billing import UsageKind
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.dto.conversation_engine import PreparedTurn, ReplyRecord
from app.schemas.typings.billing.constrained_integers import (
    CostMicroUsd,
    UsageQuantity,
)
from app.utilities.conversations.llm_models import LlmCallCost, compute_llm_call_cost


def verifier_costs(record: ReplyRecord) -> list[tuple[int, int, LlmCallCost]]:
    """(input tokens, output tokens, cost) of each verifier call."""

    return [
        (
            int(usage.input_tokens),
            int(usage.output_tokens),
            compute_llm_call_cost(
                usage.model_id, usage.input_tokens, usage.output_tokens
            ),
        )
        for usage in record.verifier_usage
    ]


def total_verifier_cost(record: ReplyRecord) -> CostMicroUsd:
    return CostMicroUsd(sum(int(cost.total) for _, _, cost in verifier_costs(record)))


def record_reply_usage(
    usage_event_repo: UsageEventRepoContract,
    record: ReplyRecord,
    cost: LlmCallCost,
    now: Microseconds,
) -> None:
    turn: PreparedTurn = record.turn
    usages: list[tuple[UsageKind, int, CostMicroUsd]] = [
        (UsageKind.LLM_INPUT_TOKENS, int(record.input_tokens), cost.input_cost),
        (UsageKind.LLM_OUTPUT_TOKENS, int(record.output_tokens), cost.output_cost),
    ]
    for input_tokens, output_tokens, verifier_cost in verifier_costs(record):
        usages.append(
            (UsageKind.LLM_INPUT_TOKENS, input_tokens, verifier_cost.input_cost)
        )
        usages.append(
            (UsageKind.LLM_OUTPUT_TOKENS, output_tokens, verifier_cost.output_cost)
        )

    if turn.is_new_conversation and not turn.conversation.is_sandbox:
        usages.append((UsageKind.DIALOG, 1, CostMicroUsd(0)))

    for kind, quantity, usage_cost in usages:
        if quantity == 0:
            continue

        usage_event_repo.append(
            UsageEventDocument(
                business_id=turn.business.id,
                conversation_id=turn.conversation.id,
                kind=kind,
                quantity=UsageQuantity(quantity),
                cost_micro_usd=usage_cost,
                occurred_at=now,
                created_at=now,
                updated_at=now,
            )
        )
