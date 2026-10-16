"""What "Fix this answer" reads from an answer: its scope and the items it names."""

import json

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.knowledge import AnswerCorrectionScope, KnowledgeItemKind
from app.schemas.constants.reply_safety import (
    ClaimTopic,
    ClaimVerdict,
    ReplyGuardReason,
)
from app.schemas.domain.conversations import (
    ClaimFinding,
    MessageDocument,
    ToolCallRecord,
)
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import (
    ClaimText,
    LlmToolInputJson,
    LlmToolResultJson,
    MessageText,
)
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.utilities.conversations.answer_fix_hints import (
    looked_up_item_ids,
    match_item_by_question,
    suggest_scope,
)

BUSINESS: BusinessId = BusinessId()


def answer(**fields: object) -> MessageDocument:
    return MessageDocument.model_validate(
        {
            "conversation_id": ConversationId(),
            "business_id": BUSINESS,
            "direction": MessageDirection.OUTBOUND,
            "author": MessageAuthor.ASSISTANT,
            "text": MessageText("Ответ."),
            **fields,
        }
    )


def call(
    tool: AssistantToolName, result: str, is_error: bool = False
) -> ToolCallRecord:
    return ToolCallRecord(
        tool_name=tool,
        input_json=LlmToolInputJson("{}"),
        result_json=LlmToolResultJson(result),
        is_error=is_error,
    )


def item(
    title: str,
    kind: KnowledgeItemKind = KnowledgeItemKind.MENU_ITEM,
    is_active: bool = True,
) -> KnowledgeItemDocument:
    return KnowledgeItemDocument(
        business_id=BUSINESS,
        kind=kind,
        title=KnowledgeTitle(title),
        price_minor=None if kind is KnowledgeItemKind.FAQ else MoneyAmountMinor(100),
        is_active=is_active,
    )


def test_the_scope_follows_the_tools_and_the_guard() -> None:
    assert (
        suggest_scope(answer(guard_reasons=[ReplyGuardReason.UNVERIFIED_VALUES]))
        is AnswerCorrectionScope.PRICE
    )
    assert (
        suggest_scope(
            answer(
                claim_findings=[
                    ClaimFinding(
                        claim=ClaimText("Dogs are welcome"),
                        topic=ClaimTopic.POLICY,
                        verdict=ClaimVerdict.UNSUPPORTED,
                    )
                ]
            )
        )
        is AnswerCorrectionScope.RULE
    )
    assert suggest_scope(answer()) is AnswerCorrectionScope.FAQ


def test_looked_up_items_skip_errors_and_unreadable_results() -> None:
    found = looked_up_item_ids(
        [
            call(AssistantToolName.GET_PRICE, json.dumps({"matches": [{"id": "a"}]})),
            call(
                AssistantToolName.GET_PRICE,
                json.dumps({"matches": [{"id": "x"}]}),
                True,
            ),
            call(AssistantToolName.SEARCH_KNOWLEDGE, "not json"),
            call(AssistantToolName.SEARCH_KNOWLEDGE, json.dumps(["a list"])),
            call(
                AssistantToolName.SEARCH_KNOWLEDGE,
                json.dumps({"items": [{"id": "b"}, {"id": 7}, "c"], "matches": None}),
            ),
            call(
                AssistantToolName.CHECK_AVAILABILITY,
                json.dumps({"items": [{"id": "z"}]}),
            ),
            call(AssistantToolName.GET_PRICE, json.dumps({"matches": [{"id": "a"}]})),
        ]
    )

    assert found == ["a", "b"]


def test_a_price_question_names_the_longest_active_offer() -> None:
    items = [
        item("Хинкали"),
        item("Хинкали с сыром"),
        item("Хинкали с сыром и зеленью", is_active=False),
        item("Сколько стоят хинкали с сыром?", KnowledgeItemKind.FAQ),
    ]

    named = match_item_by_question(
        items, "Сколько стоят хинкали с сыром?", AnswerCorrectionScope.PRICE
    )

    assert named is not None and named.title == "Хинкали с сыром"
    assert match_item_by_question(items, "?!", AnswerCorrectionScope.PRICE) is None


def test_a_question_names_the_question_of_the_same_title() -> None:
    items = [item("Хинкали"), item("Есть парковка?", KnowledgeItemKind.FAQ)]

    found = match_item_by_question(items, "есть ПАРКОВКА", AnswerCorrectionScope.FAQ)

    assert found is not None and found.kind is KnowledgeItemKind.FAQ
    assert match_item_by_question(items, "Хинкали", AnswerCorrectionScope.FAQ) is None
