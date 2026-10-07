"""What counts toward gaps: inactive records, niches, customer questions, choices."""

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.niches import NicheKey, ProfileWizardStep
from app.schemas.constants.profiles import ProfileGapKind
from app.schemas.dto.knowledge_admin import (
    CreateKnowledgeItemCommand,
    KnowledgeItemInput,
)
from app.schemas.dto.profiles.business_profile import ProfileAnswerInput
from app.schemas.dto.profiles.profile_gaps import ProfileGapsQuery
from app.schemas.dto.profiles.profile_steps import NicheAndLanguagesStepInput
from app.schemas.dto.resources import CreateResourceCommand, ResourceInput
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.bookings.constrained_integers import ResourceCapacity
from app.schemas.typings.bookings.strings import ResourceName
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.profiles.constrained_strings import (
    QuestionChoiceKey,
    QuestionKey,
)
from tests.knowledge.harness import KnowledgeHarness
from tests.knowledge.profile_gaps_helpers import add_question, kinds, save


def test_inactive_items_and_resources_do_not_count() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(has_manager_contact=True)
    harness.create_knowledge_item.run(
        CreateKnowledgeItemCommand(
            business_id=business.id,
            item=KnowledgeItemInput(
                kind=KnowledgeItemKind.MENU_ITEM,
                title=KnowledgeTitle("Old dish"),
                price_minor=MoneyAmountMinor(500),
                is_active=False,
            ),
        )
    )
    harness.create_resource.run(
        CreateResourceCommand(
            business_id=business.id,
            resource=ResourceInput(
                name=ResourceName("Closed terrace"),
                capacity=ResourceCapacity(10),
                is_active=False,
            ),
        )
    )

    view = harness.compute_profile_gaps.run(ProfileGapsQuery(business_id=business.id))

    assert ProfileGapKind.NO_PRICED_ITEMS in kinds(view)
    assert ProfileGapKind.NO_RESOURCES in kinds(view)
    assert ProfileGapKind.NO_HANDOFF_CONTACT not in kinds(view)


def test_niches_without_bookings_need_no_resources_and_address_is_advice() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(niche_key=NicheKey.ONLINE_SHOP)

    view = harness.compute_profile_gaps.run(ProfileGapsQuery(business_id=business.id))

    assert ProfileGapKind.NO_RESOURCES not in kinds(view)
    assert ProfileGapKind.NO_BOOKING_RULES not in kinds(view)
    address_gap = next(
        gap for gap in view.gaps if gap.kind is ProfileGapKind.NO_ADDRESS
    )
    assert address_gap.is_blocking is False
    required = [
        gap.question_key
        for gap in view.gaps
        if gap.kind is ProfileGapKind.MISSING_REQUIRED_ANSWER
    ]
    assert required == ["product_categories", "delivery_options"]


def test_open_customer_questions_are_listed_by_frequency_without_sandbox() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(owner_language="ru")
    other_business = harness.add_business()
    add_question(harness, business.id, "Есть ли парковка?", 2)
    add_question(harness, business.id, "Можно ли с собакой?", 7)
    add_question(harness, business.id, "Есть ли Wi-Fi?", 4, is_resolved=True)
    add_question(harness, business.id, "Тестовый вопрос", 9, is_sandbox=True)
    add_question(harness, other_business.id, "Чужой вопрос", 50)

    view = harness.compute_profile_gaps.run(ProfileGapsQuery(business_id=business.id))

    question_gaps = [
        gap for gap in view.gaps if gap.kind is ProfileGapKind.UNANSWERED_QUESTION
    ]
    assert [gap.unanswered_question for gap in question_gaps] == [
        "Можно ли с собакой?",
        "Есть ли парковка?",
    ]
    assert [gap.occurrence_count for gap in question_gaps] == [7, 2]
    assert question_gaps[0].description == (
        "Вопрос клиентов без ответа: «Можно ли с собакой?» (сколько раз задан: 7). "
        "Добавьте ответ."
    )
    assert all(gap.step is ProfileWizardStep.FAQ_AND_HANDOFF for gap in question_gaps)
    assert all(not gap.is_blocking for gap in question_gaps)


def test_required_multiple_choice_answer_closes_its_gap() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(niche_key=NicheKey.CLINIC)
    save(
        harness,
        business.id,
        NicheAndLanguagesStepInput(
            answers=[
                ProfileAnswerInput(
                    question_key=QuestionKey("specialties"),
                    choice_keys=[QuestionChoiceKey("dentistry")],
                )
            ]
        ),
    )

    view = harness.compute_profile_gaps.run(ProfileGapsQuery(business_id=business.id))

    missing = [
        gap.question_key
        for gap in view.gaps
        if gap.kind is ProfileGapKind.MISSING_REQUIRED_ANSWER
    ]
    assert missing == ["emergency_message"]
