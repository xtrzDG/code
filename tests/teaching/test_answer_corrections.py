"""
"Fix this answer": the dialog's draft, and the knowledge item each kind of
correction creates or updates, linked to the answer it corrects.
"""

import pytest

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.knowledge import AnswerCorrectionScope, KnowledgeItemKind
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from tests.brain.scripted_turns import call_tool, say
from tests.teaching.correction_helpers import fix, open_draft
from tests.teaching.teaching_world import build_teaching_world

PARKING: str = "Есть ли у вас парковка?"
PARKING_ANSWER: str = "Да, бесплатная парковка во дворе."


def test_the_draft_names_the_question_the_scope_and_is_audited() -> None:
    world = build_teaching_world(say("К сожалению, не знаю."))
    reply = world.brain.send(PARKING)
    answer = world.answer_of(reply)

    draft = open_draft(world, answer)

    assert draft.question == PARKING
    assert str(draft.answer).endswith("К сожалению, не знаю.")
    assert draft.language == "ru"
    assert draft.suggested_scope is AnswerCorrectionScope.FAQ
    assert draft.current_fact is None
    assert draft.is_corrected is False
    entry = world.brain.audit_log_repo.list_by_business(world.brain.business.id)[-1]
    assert entry.action is AuditAction.VIEW
    assert str(entry.entity) == "message"
    assert str(entry.entity_id) == str(answer.id)


def test_the_draft_finds_the_item_the_question_names() -> None:
    world = build_teaching_world(say("Нет."))
    item = KnowledgeItemDocument(
        business_id=world.brain.business.id,
        kind=KnowledgeItemKind.FAQ,
        title=KnowledgeTitle(PARKING),
        body=KnowledgeBody("Нет."),
    )
    world.brain.knowledge_item_repo.save(item)
    answer = world.answer_of(world.brain.send(PARKING))

    draft = open_draft(world, answer)

    assert draft.current_fact is not None
    assert draft.current_fact.knowledge_item_id == item.id


def test_a_looked_up_price_suggests_a_price_fix_with_its_item() -> None:
    world = build_teaching_world(
        call_tool(AssistantToolName.GET_PRICE, '{"item_name":"khinkali"}'),
        say("Хинкали — 2 лари."),
    )
    menu = world.store_menu()
    answer = world.answer_of(world.brain.send("Сколько стоят хинкали?"))

    draft = open_draft(world, answer)

    assert draft.suggested_scope is AnswerCorrectionScope.PRICE
    assert draft.current_fact is not None
    assert draft.current_fact.title == "Khinkali"
    result = fix(
        world,
        answer,
        AnswerCorrectionScope.PRICE,
        knowledge_item_id=str(draft.current_fact.knowledge_item_id),
        price_minor=150,
    )
    assert result.is_new is False
    assert result.item.knowledge_item_id == menu[1].id
    assert result.item.price_minor == 150
    stored = world.brain.knowledge_item_repo.get(world.brain.business.id, menu[1].id)
    assert stored is not None and stored.correction_of == answer.id


def test_checking_free_time_suggests_an_hours_fix() -> None:
    world = build_teaching_world(
        call_tool(
            AssistantToolName.CHECK_AVAILABILITY,
            '{"date":"2026-10-02","time":"23:30","party_size":2}',
        ),
        say("Свободно."),
    )
    answer = world.answer_of(world.brain.send("Можно в 23:30?"))

    assert open_draft(world, answer).suggested_scope is AnswerCorrectionScope.HOURS
    result = fix(
        world,
        answer,
        AnswerCorrectionScope.HOURS,
        correct_answer="Кухня работает до 23:00.",
    )

    assert result.item.kind is KnowledgeItemKind.POLICY
    assert result.question == "Можно в 23:30?"
    stored = world.brain.knowledge_item_repo.get(
        world.brain.business.id, result.item.knowledge_item_id
    )
    assert stored is not None and [str(tag) for tag in stored.tags] == ["hours"]


def test_a_rule_becomes_a_policy_and_a_question_an_faq() -> None:
    world = build_teaching_world(say("Да."), say("Нет."))
    rule_answer = world.answer_of(world.brain.send("С собакой можно?"))
    faq_answer = world.answer_of(world.brain.send(PARKING, user_id="other"))

    rule = fix(
        world,
        rule_answer,
        AnswerCorrectionScope.RULE,
        question="Собаки",
        correct_answer="Только на террасе.",
    )
    faq = fix(
        world, faq_answer, AnswerCorrectionScope.FAQ, correct_answer=PARKING_ANSWER
    )

    assert (rule.item.kind, rule.item.title) == (KnowledgeItemKind.POLICY, "Собаки")
    assert (faq.item.kind, faq.item.title) == (KnowledgeItemKind.FAQ, PARKING)
    assert rule.is_new and faq.is_new
    assert (
        world.brain.knowledge_item_repo.find_by_correction(
            world.brain.business.id, faq_answer.id
        )
        is not None
    )


def test_a_correction_updates_the_question_already_written() -> None:
    world = build_teaching_world(say("Нет."))
    written = KnowledgeItemDocument(
        business_id=world.brain.business.id,
        kind=KnowledgeItemKind.FAQ,
        title=KnowledgeTitle(PARKING),
        body=KnowledgeBody("Нет."),
        is_active=False,
    )
    world.brain.knowledge_item_repo.save(written)
    answer = world.answer_of(world.brain.send(PARKING))

    result = fix(
        world, answer, AnswerCorrectionScope.FAQ, correct_answer=PARKING_ANSWER
    )

    assert result.is_new is False
    assert result.item.knowledge_item_id == written.id
    stored = world.brain.knowledge_item_repo.get(world.brain.business.id, written.id)
    assert stored is not None
    assert stored.is_active is True
    assert stored.body == PARKING_ANSWER


def test_a_wrong_price_of_an_unknown_offer_becomes_a_new_offer() -> None:
    world = build_teaching_world(say("Не знаю."))
    answer = world.answer_of(world.brain.send("Сколько стоит лобио?"))

    result = fix(
        world,
        answer,
        AnswerCorrectionScope.PRICE,
        question="Лобио",
        price_minor=900,
    )

    assert result.is_new is True
    assert result.item.kind is KnowledgeItemKind.MENU_ITEM
    assert result.item.currency_code == "GEL"


def test_a_price_fix_needs_a_price_and_an_offer() -> None:
    world = build_teaching_world(say("Не знаю."))
    answer = world.answer_of(world.brain.send("Сколько стоит лобио?"))

    with pytest.raises(ValidationFailedError):
        fix(world, answer, AnswerCorrectionScope.PRICE)
    with pytest.raises(ValidationFailedError):
        fix(world, answer, AnswerCorrectionScope.PRICE, price_minor=900)


def test_a_price_cannot_go_on_a_question_or_an_unknown_item() -> None:
    world = build_teaching_world(say("Нет."))
    question = KnowledgeItemDocument(
        business_id=world.brain.business.id,
        kind=KnowledgeItemKind.FAQ,
        title=KnowledgeTitle(PARKING),
    )
    world.brain.knowledge_item_repo.save(question)
    answer = world.answer_of(world.brain.send(PARKING))

    with pytest.raises(ValidationFailedError):
        fix(
            world,
            answer,
            AnswerCorrectionScope.PRICE,
            knowledge_item_id=str(question.id),
            price_minor=100,
        )
    with pytest.raises(NotFoundError):
        fix(
            world,
            answer,
            AnswerCorrectionScope.PRICE,
            knowledge_item_id=str(KnowledgeItemId()),
            price_minor=100,
        )


def test_a_text_fix_needs_the_answer() -> None:
    world = build_teaching_world(say("Нет."))
    answer = world.answer_of(world.brain.send(PARKING))

    with pytest.raises(ValidationFailedError):
        fix(world, answer, AnswerCorrectionScope.FAQ)


def test_only_an_owner_fixes_only_an_answer_of_the_assistant() -> None:
    world = build_teaching_world(say("Нет."))
    reply = world.brain.send(PARKING)
    answer = world.answer_of(reply)
    customer_message = next(
        message
        for message in world.messages(reply.conversation_id)
        if message.author is MessageAuthor.CUSTOMER
    )

    with pytest.raises(AccessDeniedError):
        open_draft(world, answer, world.brain.staff_id)
    with pytest.raises(AccessDeniedError):
        fix(
            world,
            answer,
            AnswerCorrectionScope.FAQ,
            world.brain.staff_id,
            correct_answer=PARKING_ANSWER,
        )
    with pytest.raises(ValidationFailedError):
        open_draft(world, customer_message)
    with pytest.raises(NotFoundError):
        open_draft(
            world,
            answer.model_copy(update={"conversation_id": ConversationId()}),
        )
