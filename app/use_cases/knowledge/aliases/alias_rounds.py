"""
One round of alias suggestions: which items need aliases in which
languages, one model call for them, the suggestions stored next to what
the owner wrote meanwhile, and the call recorded as the business's usage.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.contracts.knowledge_aliases import KnowledgeAliasSuggesterContract
from app.contracts.localization_utilities import LanguageDetectorContract
from app.contracts.repositories.billing_repositories import UsageEventRepoContract
from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.schemas.constants.billing import UsageKind
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.knowledge_aliases import (
    AliasSuggestionItem,
    AliasSuggestionRequest,
    AliasSuggestionResult,
)
from app.schemas.typings.billing.constrained_integers import UsageQuantity
from app.schemas.typings.knowledge.constrained_strings import KnowledgeAliasText
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.conversations.llm_models import LlmCallCost, compute_llm_call_cost
from app.utilities.knowledge.aliases.alias_targets import (
    add_suggested_aliases,
    item_languages,
    missing_alias_languages,
)

# One call names this many items: about 4,000 output tokens for three
# languages, well inside the call's limit.
MAX_ITEMS_PER_CALL: int = 40


@dataclass(frozen=True)
class AliasRoundOutcome:
    """What one round did: items asked about, items given new aliases."""

    asked_count: int
    updated_count: int


def plan_alias_items(
    items: Sequence[KnowledgeItemDocument],
    business: BusinessDocument,
    language_detector: LanguageDetectorContract,
) -> list[AliasSuggestionItem]:
    """
    The active, confirmed items that lack an alias in one of the business's
    languages, questions first (they become starter questions), then in
    the given order.
    """

    planned: list[AliasSuggestionItem] = []
    for item in items:
        if not item.is_active or item.import_batch_id is not None:
            continue

        own: list[LanguageTag] = item_languages(
            item, business.languages, business.default_language, language_detector
        )
        missing: list[LanguageTag] = missing_alias_languages(
            item, business.languages, own
        )
        if missing:
            planned.append(
                AliasSuggestionItem(
                    item_id=item.id,
                    kind=item.kind,
                    title=item.title,
                    source_languages=own,
                    target_languages=missing,
                )
            )

    return sorted(
        planned, key=lambda planned_item: planned_item.kind is not KnowledgeItemKind.FAQ
    )


def run_alias_round(
    suggester: KnowledgeAliasSuggesterContract,
    knowledge_item_repo: KnowledgeItemRepoContract,
    usage_event_repo: UsageEventRepoContract,
    business: BusinessDocument,
    items: Sequence[AliasSuggestionItem],
    now: Microseconds,
) -> AliasRoundOutcome:
    """
    One model call for up to `MAX_ITEMS_PER_CALL` items, its cost recorded,
    and each item's suggestions stored in one atomic step with the item as
    it is stored then (an edit made during the call is kept; suggestions
    for a title that changed meanwhile are dropped). Adding suggestions
    changes nothing the assistant's version holds, so `updated_at` stays.
    """

    asked: list[AliasSuggestionItem] = list(items[:MAX_ITEMS_PER_CALL])
    if asked == []:
        return AliasRoundOutcome(asked_count=0, updated_count=0)

    result: AliasSuggestionResult = suggester.suggest(
        AliasSuggestionRequest(items=asked)
    )
    record_alias_usage(usage_event_repo, business, result, now)
    updated: int = 0
    for item in asked:
        suggestions: list[tuple[LanguageTag, KnowledgeAliasText]] = [
            (alias.language, alias.text)
            for alias in result.aliases
            if alias.item_id == item.item_id
        ]
        if suggestions and store_suggestions(
            knowledge_item_repo, business, item, suggestions
        ):
            updated += 1

    return AliasRoundOutcome(asked_count=len(asked), updated_count=updated)


def store_suggestions(
    knowledge_item_repo: KnowledgeItemRepoContract,
    business: BusinessDocument,
    item: AliasSuggestionItem,
    suggestions: Sequence[tuple[LanguageTag, KnowledgeAliasText]],
) -> bool:
    """Whether the item got any of the suggestions (see `add_suggested_aliases`)."""

    def change(stored: KnowledgeItemDocument) -> KnowledgeItemDocument | None:
        return add_suggested_aliases(stored, suggestions, item.title)

    item_id: KnowledgeItemId = item.item_id
    return knowledge_item_repo.update(business.id, item_id, change) is not None


def record_alias_usage(
    usage_event_repo: UsageEventRepoContract,
    business: BusinessDocument,
    result: AliasSuggestionResult,
    now: Microseconds,
) -> None:
    """The call's tokens as usage events, each with its cost at list price."""

    cost: LlmCallCost = compute_llm_call_cost(
        result.model_id, result.input_tokens, result.output_tokens
    )
    for kind, quantity, usage_cost in (
        (UsageKind.LLM_INPUT_TOKENS, int(result.input_tokens), cost.input_cost),
        (UsageKind.LLM_OUTPUT_TOKENS, int(result.output_tokens), cost.output_cost),
    ):
        if quantity == 0:
            continue

        usage_event_repo.append(
            UsageEventDocument(
                business_id=business.id,
                kind=kind,
                quantity=UsageQuantity(quantity),
                cost_micro_usd=usage_cost,
                occurred_at=now,
                created_at=now,
                updated_at=now,
            )
        )
