import re

import pytest
from pydantic import ValidationError

from app.registries.niches.niche_template_registry import NicheTemplateRegistry
from app.registries.niches.template_parts import (
    BASE_AUTOTEST_KINDS,
    COMMON_FORBIDDEN_RULES_EN,
)
from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.constants.bookings import BookingUnit
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.niches import (
    LaunchWave,
    NicheKey,
    ProfileWizardStep,
    QuestionAnswerType,
)
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.niches import NicheTemplate
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.knowledge.localized_texts import split_rule_lines

ENGLISH: LanguageTag = LanguageTag("en")
REGISTRY: NicheTemplateRegistry = NicheTemplateRegistry()
TEMPLATES: list[NicheTemplate] = REGISTRY.list_all()
CHOICE_TYPES: frozenset[QuestionAnswerType] = frozenset(
    {QuestionAnswerType.SINGLE_CHOICE, QuestionAnswerType.MULTIPLE_CHOICE}
)
NON_LATIN_LETTER: re.Pattern[str] = re.compile(r"[^\x00-\x7F’“”–—]")


def template_id(template: NicheTemplate) -> str:
    return template.key.value


def has_languages(text: LocalizedText, *languages: str) -> bool:
    return all(
        LanguageTag(language) in text.values
        and text.values[LanguageTag(language)].strip() != ""
        for language in languages
    )


def test_registry_has_one_template_for_each_of_the_16_niches() -> None:
    keys: list[NicheKey] = [template.key for template in TEMPLATES]

    assert len(TEMPLATES) == 16
    assert set(keys) == set(NicheKey)
    assert len(set(keys)) == len(keys)
    for niche_key in NicheKey:
        assert REGISTRY.get(niche_key).key is niche_key


def test_registry_returns_immutable_templates_and_fresh_lists() -> None:
    template: NicheTemplate = REGISTRY.get(NicheKey.RESTAURANT)

    with pytest.raises(ValidationError):
        setattr(template, "takes_bookings", False)  # noqa: B010

    REGISTRY.list_all().clear()
    assert len(REGISTRY.list_all()) == 16


@pytest.mark.parametrize("template", TEMPLATES, ids=template_id)
def test_display_texts_exist_in_english_russian_and_georgian(
    template: NicheTemplate,
) -> None:
    assert has_languages(template.names, "en", "ru", "ka")
    assert has_languages(template.descriptions, "en", "ru", "ka")
    assert has_languages(template.resource_nouns, "en", "ru", "ka")
    assert has_languages(template.default_handoff_rules, "en", "ru", "ka")
    assert has_languages(template.default_forbidden_rules, "en", "ru", "ka")


@pytest.mark.parametrize("template", TEMPLATES, ids=template_id)
def test_every_question_label_hint_and_choice_has_english_and_russian(
    template: NicheTemplate,
) -> None:
    for question in template.questions:
        assert has_languages(question.labels, "en", "ru"), question.key
        if question.hints is not None:
            assert has_languages(question.hints, "en", "ru"), question.key

        for choice in question.choices:
            assert has_languages(choice.labels, "en", "ru"), choice.key


@pytest.mark.parametrize("template", TEMPLATES, ids=template_id)
def test_question_and_fact_keys_are_unique_within_a_niche(
    template: NicheTemplate,
) -> None:
    question_keys: list[str] = [question.key for question in template.questions]
    fact_keys: list[str] = [question.fact_key for question in template.questions]

    assert len(set(question_keys)) == len(question_keys)
    assert len(set(fact_keys)) == len(fact_keys)


@pytest.mark.parametrize("template", TEMPLATES, ids=template_id)
def test_choices_match_answer_types(template: NicheTemplate) -> None:
    for question in template.questions:
        choice_keys: list[str] = [choice.key for choice in question.choices]
        assert len(set(choice_keys)) == len(choice_keys), question.key
        if question.answer_type in CHOICE_TYPES:
            assert len(choice_keys) >= 2, question.key
        elif question.answer_type is QuestionAnswerType.YES_NO:
            assert choice_keys == ["yes", "no"], question.key
        else:
            assert choice_keys == [], question.key


@pytest.mark.parametrize("template", TEMPLATES, ids=template_id)
def test_wizard_stays_short_with_few_required_questions(
    template: NicheTemplate,
) -> None:
    required_count: int = sum(question.is_required for question in template.questions)

    assert 1 <= required_count <= 3
    assert len(template.questions) <= 12
    assert any(
        question.step is ProfileWizardStep.NICHE_AND_LANGUAGES
        for question in template.questions
    )


@pytest.mark.parametrize("template", TEMPLATES, ids=template_id)
def test_platform_rules_and_autotests_are_shared_by_every_niche(
    template: NicheTemplate,
) -> None:
    rule_texts: list[str] = [str(rule) for rule in template.prompt_rules]
    forbidden_en: list[str] = split_rule_lines(
        template.default_forbidden_rules.values[ENGLISH]
    )

    # Platform rules are stated once, in the instruction sections.
    assert 2 <= len(rule_texts) <= 6
    assert all(NON_LATIN_LETTER.search(rule) is None for rule in rule_texts)
    assert not any("AI assistant" in rule for rule in rule_texts)
    assert forbidden_en[: len(COMMON_FORBIDDEN_RULES_EN)] == list(
        COMMON_FORBIDDEN_RULES_EN
    )
    assert template.autotest_kinds[: len(BASE_AUTOTEST_KINDS)] == list(
        BASE_AUTOTEST_KINDS
    )
    assert KnowledgeItemKind.FAQ in template.knowledge_kinds
    assert KnowledgeItemKind.POLICY in template.knowledge_kinds
    assert template.recommended_plans != []


@pytest.mark.parametrize("template", TEMPLATES, ids=template_id)
def test_default_rules_list_the_same_number_of_rules_in_every_language(
    template: NicheTemplate,
) -> None:
    for rules in (template.default_handoff_rules, template.default_forbidden_rules):
        counts: set[int] = {
            len(split_rule_lines(value)) for value in rules.values.values()
        }
        assert len(counts) == 1
        assert counts.pop() >= 2


def test_hotels_and_short_term_rentals_book_nights_and_others_book_slots() -> None:
    night_niches: set[NicheKey] = {
        template.key
        for template in TEMPLATES
        if template.booking_unit is BookingUnit.NIGHT
    }

    assert night_niches == {NicheKey.HOTEL, NicheKey.SHORT_TERM_RENTAL}


def test_only_shops_and_suppliers_take_orders_instead_of_bookings() -> None:
    non_booking_niches: set[NicheKey] = {
        template.key for template in TEMPLATES if not template.takes_bookings
    }

    assert non_booking_niches == {NicheKey.ONLINE_SHOP, NicheKey.B2B_SUPPLY}


def test_health_niches_need_emergency_tests_and_clinics_need_a_lawyer() -> None:
    emergency_niches: set[NicheKey] = {
        template.key
        for template in TEMPLATES
        if AutotestScenarioKind.EMERGENCY in template.autotest_kinds
    }
    legal_review_niches: set[NicheKey] = {
        template.key for template in TEMPLATES if template.requires_legal_review
    }
    clinic: NicheTemplate = REGISTRY.get(NicheKey.CLINIC)

    assert emergency_niches == {NicheKey.CLINIC, NicheKey.VETERINARY}
    assert legal_review_niches == {NicheKey.CLINIC}
    assert any("Never give medical advice" in rule for rule in clinic.prompt_rules)
    assert any(
        "medical advice" in rule.casefold()
        for rule in split_rule_lines(clinic.default_forbidden_rules.values[ENGLISH])
    )


def test_first_wave_niches_follow_the_concept() -> None:
    wave_a: set[NicheKey] = {
        template.key for template in TEMPLATES if template.wave is LaunchWave.A
    }

    assert wave_a == {
        NicheKey.RESTAURANT,
        NicheKey.HOTEL,
        NicheKey.ENTERTAINMENT,
        NicheKey.BEAUTY_SALON,
    }


@pytest.mark.parametrize(
    ("niche_key", "expected_question_keys"),
    [
        (
            NicheKey.RESTAURANT,
            {"banquets", "delivery", "live_music", "kids_menu", "allergen_policy"},
        ),
        (
            NicheKey.HOTEL,
            {
                "seasonal_prices",
                "check_in_time",
                "check_out_time",
                "transfer",
                "breakfast",
                "booking_system",
            },
        ),
        (
            NicheKey.BEAUTY_SALON,
            {"masters_and_services", "break_between_appointments"},
        ),
        (NicheKey.CLINIC, {"doctors", "visit_preparation", "emergency_message"}),
        (
            NicheKey.ENTERTAINMENT,
            {"birthday_packages", "min_age", "visitor_rules", "prepayment"},
        ),
        (NicheKey.CAR_SERVICE, {"services_offered", "what_to_bring"}),
        (
            NicheKey.CAR_RENTAL_AND_TOURS,
            {"fleet", "security_deposit", "driver_requirements"},
        ),
        (NicheKey.EVENT_VENUE, {"lead_fields", "max_guests"}),
        (NicheKey.REAL_ESTATE, {"lead_fields", "installment_plans"}),
        (NicheKey.EDUCATION, {"lead_fields", "trial_lesson"}),
        (NicheKey.ONLINE_SHOP, {"lead_fields", "delivery_options"}),
        (NicheKey.HOME_SERVICES, {"lead_fields", "service_area"}),
        (NicheKey.B2B_SUPPLY, {"lead_fields", "delivery_terms"}),
        (NicheKey.VETERINARY, {"animals_treated", "emergency_hours"}),
        (NicheKey.FITNESS, {"trial_session", "membership_freeze"}),
        (
            NicheKey.SHORT_TERM_RENTAL,
            {"check_in_instructions", "wifi_info", "house_rules"},
        ),
    ],
)
def test_niche_modules_ask_the_concept_questions(
    niche_key: NicheKey,
    expected_question_keys: set[str],
) -> None:
    question_keys: set[str] = {
        question.key for question in REGISTRY.get(niche_key).questions
    }

    assert expected_question_keys <= question_keys
