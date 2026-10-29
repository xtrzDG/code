"""
What "Fix this answer" can tell from the answer itself: the kind of
correction it most likely needs, and the knowledge items the assistant
looked up for it (get_price and search_knowledge results name them).
"""

import json
from collections.abc import Sequence
from typing import cast

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.knowledge import AnswerCorrectionScope, KnowledgeItemKind
from app.schemas.constants.reply_safety import ClaimTopic, ReplyGuardReason
from app.schemas.domain.conversations import MessageDocument, ToolCallRecord
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.utilities.knowledge.search_text import fold_words

LOOKUP_TOOLS: frozenset[AssistantToolName] = frozenset(
    {AssistantToolName.GET_PRICE, AssistantToolName.SEARCH_KNOWLEDGE}
)
RESULT_LISTS: tuple[str, ...] = ("matches", "items")
QUESTION_KINDS: frozenset[KnowledgeItemKind] = frozenset(
    {KnowledgeItemKind.FAQ, KnowledgeItemKind.POLICY}
)


def suggest_scope(answer: MessageDocument) -> AnswerCorrectionScope:
    """
    PRICE when the assistant looked a price up or the guard found values it
    could not back, HOURS when it checked free time, RULE when the guard
    doubted a policy claim, else a question and its answer (FAQ).
    """

    tools: set[AssistantToolName] = {call.tool_name for call in answer.tool_calls}
    if (
        AssistantToolName.GET_PRICE in tools
        or ReplyGuardReason.UNVERIFIED_VALUES in answer.guard_reasons
    ):
        return AnswerCorrectionScope.PRICE

    if AssistantToolName.CHECK_AVAILABILITY in tools:
        return AnswerCorrectionScope.HOURS

    if any(finding.topic is ClaimTopic.POLICY for finding in answer.claim_findings):
        return AnswerCorrectionScope.RULE

    return AnswerCorrectionScope.FAQ


def looked_up_item_ids(tool_calls: Sequence[ToolCallRecord]) -> list[str]:
    """The ids of the items get_price and search_knowledge answered with."""

    found: list[str] = []
    for call in tool_calls:
        if call.tool_name not in LOOKUP_TOOLS or call.is_error:
            continue

        try:
            result: object = json.loads(str(call.result_json))
        except ValueError:
            continue

        if not isinstance(result, dict):
            continue

        fields: dict[object, object] = cast(dict[object, object], result)
        for key in RESULT_LISTS:
            entries: object = fields.get(key)
            if not isinstance(entries, list):
                continue

            for entry in cast(list[object], entries):
                if not isinstance(entry, dict):
                    continue

                item_id: object = cast(dict[object, object], entry).get("id")
                if isinstance(item_id, str):
                    found.append(item_id)

    return list(dict.fromkeys(found))


def match_item_by_question(
    items: Sequence[KnowledgeItemDocument],
    question: str,
    scope: AnswerCorrectionScope,
) -> KnowledgeItemDocument | None:
    """
    For a price, the active offer whose title the question names (the
    longest such title); otherwise the question or rule of the same title.
    """

    folded_question: str = fold_words(question)
    if folded_question == "":
        return None

    if scope is AnswerCorrectionScope.PRICE:
        named: list[KnowledgeItemDocument] = [
            item
            for item in items
            if item.is_active
            and item.kind not in QUESTION_KINDS
            and fold_words(item.title) != ""
            and f" {fold_words(item.title)} " in f" {folded_question} "
        ]
        return max(named, key=lambda item: len(str(item.title)), default=None)

    for item in items:
        if item.kind in QUESTION_KINDS and fold_words(item.title) == folded_question:
            return item

    return None
