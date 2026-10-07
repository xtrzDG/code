"""Profile gaps: blocking ones first, localized texts, readiness and advice."""

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.profiles import ProfileGapKind
from app.schemas.dto.knowledge_admin import (
    CreateKnowledgeItemCommand,
    KnowledgeItemInput,
)
from app.schemas.dto.profiles.profile_gaps import ProfileGapsQuery
from app.schemas.dto.profiles.profile_wizard import ProfileWizardQuery
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.knowledge.harness import KnowledgeHarness
from tests.knowledge.profile_gaps_helpers import complete_restaurant, kinds


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
