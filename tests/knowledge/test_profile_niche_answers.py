"""Niche answers: validation, normalization, phone hints and niche changes."""

import pytest

from app.schemas.constants.niches import NicheKey
from app.schemas.dto.profiles.business_profile import ProfileAnswerInput
from app.schemas.dto.profiles.profile_steps import (
    ContactsAndHoursStepInput,
    NicheAndLanguagesStepInput,
    OfferStepInput,
)
from app.schemas.dto.profiles.profile_wizard import ProfileWizardQuery
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.profiles.constrained_strings import QuestionKey
from tests.knowledge.harness import KnowledgeHarness
from tests.knowledge.wizard_helpers import answer, choices, save_step


def test_niche_answers_are_validated_and_normalized() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(niche_key=NicheKey.RESTAURANT)

    result = save_step(
        harness,
        business.id,
        OfferStepInput(
            answers=[
                choices("banquets", "separate_hall"),
                answer("banquet_max_guests", "٤٠"),
                choices("dietary_options", "vegan", "vegetarian"),
                answer("kids_menu", "YES"),
                choices("outdoor_seating", "no"),
                ProfileAnswerInput(question_key=QuestionKey("live_music")),
            ]
        ),
    )

    stored = {item.question_key: item.answer for item in result.profile.niche_answers}
    assert stored == {
        "banquets": "separate_hall",
        "banquet_max_guests": "40",
        "kids_menu": "yes",
        "outdoor_seating": "no",
        "dietary_options": "vegetarian,vegan",
    }
    wizard = harness.get_profile_wizard.run(ProfileWizardQuery(business_id=business.id))
    offer_step = wizard.steps[2]
    dietary = next(
        question
        for question in offer_step.questions
        if question.question.key == "dietary_options"
    )
    assert dietary.selected_choice_keys == ["vegetarian", "vegan"]


@pytest.mark.parametrize(
    ("step_input", "message"),
    [
        (OfferStepInput(answers=[answer("unknown_question", "x")]), "does not exist"),
        (OfferStepInput(answers=[answer("cuisine", "Georgian")]), "belongs to step"),
        (
            OfferStepInput(
                answers=[answer("live_music", "Fri"), answer("live_music", "Sat")]
            ),
            "twice",
        ),
        (OfferStepInput(answers=[answer("banquet_max_guests", "-3")]), "number"),
        (OfferStepInput(answers=[answer("banquet_max_guests", "2.5")]), "number"),
        (OfferStepInput(answers=[choices("banquets", "maybe")]), "not a choice"),
        (
            OfferStepInput(answers=[choices("banquets", "no", "whole_venue")]),
            "exactly one",
        ),
        (OfferStepInput(answers=[answer("banquets", "no")]), "choice_keys"),
        (OfferStepInput(answers=[choices("live_music", "no")]), "text"),
        (OfferStepInput(answers=[answer("kids_menu", "perhaps")]), "yes"),
        (
            OfferStepInput(answers=[choices("dietary_options", "vegan", "vegan")]),
            "repeats",
        ),
        (OfferStepInput(answers=[answer("live_music", "x" * 301)]), "longer"),
    ],
)
def test_invalid_niche_answers_are_rejected(
    step_input: OfferStepInput,
    message: str,
) -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(niche_key=NicheKey.RESTAURANT)

    with pytest.raises(ValidationFailedError, match=message):
        save_step(harness, business.id, step_input)


def test_phone_answers_use_the_business_country_as_a_hint() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(
        niche_key=NicheKey.SHORT_TERM_RENTAL,
        country_code="AM",
        currency_code="AMD",
        timezone="Asia/Yerevan",
        languages=("hy", "ru", "en"),
        owner_language="ru",
    )

    result = save_step(
        harness,
        business.id,
        ContactsAndHoursStepInput(answers=[answer("host_phone", "077 123456")]),
    )

    assert result.profile.niche_answers[0].answer == "+37477123456"


def test_answers_of_a_previous_niche_are_dropped_after_a_niche_change() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(niche_key=NicheKey.RESTAURANT)
    save_step(
        harness,
        business.id,
        NicheAndLanguagesStepInput(answers=[answer("cuisine", "Georgian")]),
    )
    business.niche_key = NicheKey.ENTERTAINMENT
    harness.business_repo.save(business)

    result = save_step(
        harness,
        business.id,
        NicheAndLanguagesStepInput(answers=[choices("venue_type", "vr_club")]),
    )

    assert result.profile.niche_key is NicheKey.ENTERTAINMENT
    assert [item.question_key for item in result.profile.niche_answers] == [
        "venue_type"
    ]
