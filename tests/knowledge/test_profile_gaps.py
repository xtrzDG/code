from typed_time_provider import Microseconds

from app.schemas.constants.businesses import Weekday
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.niches import NicheKey, ProfileWizardStep
from app.schemas.constants.profiles import ProfileGapKind
from app.schemas.domain.handoffs import UnansweredQuestionDocument
from app.schemas.domain.profiles import BusinessAddress, OpeningInterval
from app.schemas.dto.knowledge_admin import (
    CreateKnowledgeItemCommand,
    KnowledgeItemInput,
)
from app.schemas.dto.profiles import (
    BookingRulesInput,
    BookingRulesStepInput,
    ContactsAndHoursStepInput,
    ContactsInput,
    NicheAndLanguagesStepInput,
    ProfileAnswerInput,
    ProfileGapsQuery,
    ProfileGapsView,
    ProfileStepInput,
    ProfileWizardQuery,
    SaveProfileStepCommand,
)
from app.schemas.dto.resources import CreateResourceCommand, ResourceInput
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.bookings.constrained_integers import (
    PartySize,
    ResourceCapacity,
)
from app.schemas.typings.bookings.strings import ResourceName
from app.schemas.typings.businesses.constrained_integers import (
    ClosingMinuteOfDay,
    OpeningMinuteOfDay,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import AddressText
from app.schemas.typings.handoffs.constrained_integers import (
    QuestionOccurrenceCount,
)
from app.schemas.typings.handoffs.strings import UnansweredQuestionText
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.profiles.constrained_strings import (
    QuestionChoiceKey,
    QuestionKey,
)
from app.schemas.typings.profiles.strings import RawProfileAnswerText
from app.schemas.typings.users.prefixed_id import UserId
from tests.knowledge.harness import KnowledgeHarness


def kinds(view: ProfileGapsView) -> list[ProfileGapKind]:
    return [gap.kind for gap in view.gaps]


def save(
    harness: KnowledgeHarness,
    business_id: BusinessId,
    step_input: ProfileStepInput,
) -> None:
    harness.save_profile_step.run(
        SaveProfileStepCommand(
            business_id=business_id,
            actor_id=UserId(),
            step_input=step_input,
        )
    )


def add_question(
    harness: KnowledgeHarness,
    business_id: BusinessId,
    text: str,
    count: int,
    is_resolved: bool = False,
    is_sandbox: bool = False,
) -> None:
    harness.unanswered_question_repo.save(
        UnansweredQuestionDocument(
            business_id=business_id,
            question=UnansweredQuestionText(text),
            language=LanguageTag("ru"),
            occurrence_count=QuestionOccurrenceCount(count),
            last_seen_at=Microseconds(1_790_000_000_000_000),
            is_resolved=is_resolved,
            is_sandbox=is_sandbox,
        )
    )


def complete_restaurant(harness: KnowledgeHarness, business_id: BusinessId) -> None:
    save(
        harness,
        business_id,
        NicheAndLanguagesStepInput(
            answers=[
                ProfileAnswerInput(
                    question_key=QuestionKey("cuisine"),
                    answer=RawProfileAnswerText("Georgian"),
                )
            ]
        ),
    )
    save(
        harness,
        business_id,
        ContactsAndHoursStepInput(
            address=BusinessAddress(text=AddressText("Tbilisi, Rustaveli 1")),
            hours=[
                OpeningInterval(
                    weekday=Weekday.MONDAY,
                    opens_at=OpeningMinuteOfDay(720),
                    closes_at=ClosingMinuteOfDay(1380),
                )
            ],
            contacts=ContactsInput(
                handoff_phone_number=RawPhoneNumberInput("599123456")
            ),
        ),
    )
    save(
        harness,
        business_id,
        BookingRulesStepInput(
            booking_rules=BookingRulesInput(max_party_size=PartySize(12))
        ),
    )
    harness.create_resource.run(
        CreateResourceCommand(
            business_id=business_id,
            resource=ResourceInput(
                name=ResourceName("Table 1"),
                capacity=ResourceCapacity(4),
            ),
        )
    )


def test_empty_profile_lists_blocking_gaps_first_in_wizard_order() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()

    view = harness.compute_profile_gaps.run(ProfileGapsQuery(business_id=business.id))

    assert view.language == "ka"
    assert kinds(view) == [
        ProfileGapKind.MISSING_REQUIRED_ANSWER,
        ProfileGapKind.NO_OPENING_HOURS,
        ProfileGapKind.NO_ADDRESS,
        ProfileGapKind.NO_HANDOFF_CONTACT,
        ProfileGapKind.NO_BOOKING_RULES,
        ProfileGapKind.NO_RESOURCES,
        ProfileGapKind.NO_PRICED_ITEMS,
        ProfileGapKind.NO_FAQ,
    ]
    assert [gap.is_blocking for gap in view.gaps] == [True] * 6 + [False] * 2
    assert view.gaps[0].question_key == "cuisine"
    assert view.gaps[0].description == "უპასუხეთ კითხვას „რა სამზარეულო გაქვთ?“."
    assert view.gaps[5].description == "დაამატეთ, რას ჯავშნიან კლიენტები (მაგიდა)."
    assert view.is_ready_for_assembly is False


def test_gap_texts_follow_the_requested_language_with_english_fallback() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(niche_key=NicheKey.HOTEL)

    russian = harness.compute_profile_gaps.run(
        ProfileGapsQuery(business_id=business.id, language=LanguageTag("ru"))
    )
    arabic = harness.compute_profile_gaps.run(
        ProfileGapsQuery(business_id=business.id, language=LanguageTag("ar"))
    )

    assert (
        russian.gaps[0].description
        == "Ответьте на вопрос «Какой у вас тип размещения?»."
    )
    assert arabic.gaps[0].description == (
        "Answer the question “What kind of property is it?”."
    )
    assert "(room)" in next(
        gap.description
        for gap in arabic.gaps
        if gap.kind is ProfileGapKind.NO_RESOURCES
    )


def test_complete_profile_is_ready_and_only_advice_remains() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(has_manager_contact=True)
    complete_restaurant(harness, business.id)

    view = harness.compute_profile_gaps.run(ProfileGapsQuery(business_id=business.id))

    assert kinds(view) == [ProfileGapKind.NO_PRICED_ITEMS, ProfileGapKind.NO_FAQ]
    assert view.is_ready_for_assembly is True
    wizard = harness.get_profile_wizard.run(ProfileWizardQuery(business_id=business.id))
    assert all(step.is_complete for step in wizard.steps)


def test_priced_items_and_faq_close_the_advice_gaps() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(has_manager_contact=True)
    complete_restaurant(harness, business.id)
    for item in (
        KnowledgeItemInput(
            kind=KnowledgeItemKind.MENU_ITEM,
            title=KnowledgeTitle("Khinkali"),
            price_minor=MoneyAmountMinor(120),
        ),
        KnowledgeItemInput(
            kind=KnowledgeItemKind.FAQ,
            title=KnowledgeTitle("Parking?"),
            body=KnowledgeBody("Free, in the yard"),
        ),
    ):
        harness.create_knowledge_item.run(
            CreateKnowledgeItemCommand(business_id=business.id, item=item)
        )

    view = harness.compute_profile_gaps.run(ProfileGapsQuery(business_id=business.id))

    assert view.gaps == []
    assert view.is_ready_for_assembly is True


def test_a_handoff_phone_alone_reaches_nobody_and_stays_blocking() -> None:
    # Handoffs, bookings and leads are sent only to manager contacts; with
    # just the profile's handoff phone every staff notification is lost.
    harness = KnowledgeHarness()
    business = harness.add_business()
    complete_restaurant(harness, business.id)

    view = harness.compute_profile_gaps.run(
        ProfileGapsQuery(business_id=business.id, language=LanguageTag("en"))
    )

    assert kinds(view)[0] is ProfileGapKind.NO_HANDOFF_CONTACT
    assert view.gaps[0].is_blocking is True
    assert view.gaps[0].description.startswith("Add a manager contact")
    assert view.is_ready_for_assembly is False


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
