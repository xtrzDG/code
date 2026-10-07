"""The niche catalog and the six-step wizard in the owner's language."""

import pytest

from app.schemas.constants.niches import NicheKey, ProfileWizardStep
from app.schemas.dto.profiles.niche_catalog import NicheCatalogQuery, NicheTemplateQuery
from app.schemas.dto.profiles.profile_wizard import ProfileWizardQuery
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.profiles.strings import ForbiddenRuleText
from tests.knowledge.harness import KnowledgeHarness


def test_catalog_lists_all_niches_in_the_requested_language() -> None:
    harness = KnowledgeHarness()

    russian = harness.list_niche_templates.run(
        NicheCatalogQuery(language=LanguageTag("ru"))
    )
    fallback = harness.list_niche_templates.run(NicheCatalogQuery())
    hebrew = harness.list_niche_templates.run(
        NicheCatalogQuery(language=LanguageTag("he"))
    )
    french = harness.list_niche_templates.run(
        NicheCatalogQuery(language=LanguageTag("fr"))
    )

    assert len(russian.niches) == 16
    assert russian.niches[0].name == "Рестораны и кафе"
    assert fallback.language == "en"
    assert fallback.niches[0].name == "Restaurants and cafes"
    assert hebrew.niches[0].name == "מסעדות ובתי קפה"
    assert french.niches[0].name == "Restaurants and cafes"


def test_catalog_carries_each_niches_typical_check_in_euro() -> None:
    harness = KnowledgeHarness()

    niches = {
        niche.key: niche
        for niche in harness.list_niche_templates.run(NicheCatalogQuery()).niches
    }

    restaurant_check = niches[NicheKey.RESTAURANT].typical_check
    assert restaurant_check is not None
    assert restaurant_check.currency_code == "EUR"
    assert restaurant_check.amount_minor > 0
    # Real estate checks vary too much to guess: the calculator asks.
    assert niches[NicheKey.REAL_ESTATE].typical_check is None


def test_niche_details_resolve_questions_and_default_rules() -> None:
    harness = KnowledgeHarness()

    details = harness.get_niche_template.run(
        NicheTemplateQuery(niche_key=NicheKey.CLINIC, language=LanguageTag("ka-GE"))
    )

    assert details.niche.name == "სტომატოლოგიები და კერძო კლინიკები"
    assert details.niche.requires_legal_review is True
    assert details.questions[0].label == "რა მიმართულებებია კლინიკაში?"
    assert (
        details.default_handoff_rules[0] == "სასწრაფო სიმპტომები ან საგანგებო ვითარება"
    )
    assert len(details.default_forbidden_rules) == 4
    assert all(
        isinstance(rule, ForbiddenRuleText) for rule in details.default_forbidden_rules
    )


def test_wizard_has_six_steps_with_localized_questions_and_blank_profile() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(niche_key=NicheKey.HOTEL, owner_language="ru")

    wizard = harness.get_profile_wizard.run(ProfileWizardQuery(business_id=business.id))

    assert wizard.language == "ru"
    assert [step.step for step in wizard.steps] == list(ProfileWizardStep)
    assert [step.number for step in wizard.steps] == [1, 2, 3, 4, 5, 6]
    assert wizard.steps[0].title == "Ниша и языки"
    assert wizard.steps[0].questions[0].question.label == "Какой у вас тип размещения?"
    assert wizard.currency_code == "GEL"
    assert wizard.timezone == "Asia/Tbilisi"
    assert wizard.niche.booking_unit == "night"
    assert wizard.profile.is_saved is False
    assert wizard.default_handoff_rules[0] == "Жалоба во время проживания"
    assert not wizard.steps[0].is_complete
    assert not wizard.steps[1].is_complete
    assert wizard.steps[2].is_complete
    assert wizard.steps[4].is_complete


def test_wizard_falls_back_to_english_for_languages_without_texts() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(
        country_code="TR",
        currency_code="TRY",
        timezone="Europe/Istanbul",
        languages=("tr", "en"),
        owner_language="tr",
    )

    wizard = harness.get_profile_wizard.run(ProfileWizardQuery(business_id=business.id))

    assert wizard.steps[0].title == "Niche and languages"
    assert wizard.currency_code == "TRY"


def test_wizard_of_unknown_business_is_not_found() -> None:
    harness = KnowledgeHarness()

    with pytest.raises(NotFoundError):
        harness.get_profile_wizard.run(ProfileWizardQuery(business_id=BusinessId()))
