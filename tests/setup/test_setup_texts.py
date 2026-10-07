"""
The guided setup's texts come from the owner text catalog: every step and
every action reads in every cabinet language, Hebrew and German as drafts
waiting for a native speaker, and a cabinet in either reads its own.
"""

from app.registries.localization.text_catalog_registry import TextCatalogRegistry
from app.schemas.constants.localization import (
    CABINET_LANGUAGES,
    CabinetLanguage,
    TextReviewStatus,
)
from app.schemas.constants.setup import SetupActionTarget, SetupStepCode
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    OwnerTextKey,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from app.utilities.setup.setup_texts import (
    ACTION_LABELS,
    APPLY_CHANGES_AGAIN_LABEL,
    STEP_DESCRIPTIONS,
    STEP_TITLES,
)

DRAFT_LANGUAGES: frozenset[CabinetLanguage] = frozenset(
    {CabinetLanguage.HEBREW, CabinetLanguage.GERMAN}
)


def setup_texts() -> dict[str, LocalizedText]:
    texts: dict[str, LocalizedText] = {"apply again": APPLY_CHANGES_AGAIN_LABEL}
    texts.update({f"title {code}": STEP_TITLES[code] for code in SetupStepCode})
    texts.update(
        {f"description {code}": STEP_DESCRIPTIONS[code] for code in SetupStepCode}
    )
    texts.update(
        {f"action {target}": ACTION_LABELS[target] for target in SetupActionTarget}
    )
    return texts


def setup_keys() -> list[OwnerTextKey]:
    keys: list[OwnerTextKey] = TextCatalogRegistry().list_keys()
    return [key for key in keys if str(key).startswith("setup.")]


def test_every_step_and_action_reads_in_every_cabinet_language() -> None:
    expected: set[str] = {language.value for language in CABINET_LANGUAGES}

    gaps: dict[str, set[str]] = {
        name: expected - {str(tag) for tag in text.values}
        for name, text in setup_texts().items()
    }

    assert len(gaps) == 2 * len(SetupStepCode) + len(SetupActionTarget) + 1
    assert {name: gap for name, gap in gaps.items() if gap} == {}


def test_every_setup_key_exists_in_every_catalog_file() -> None:
    registry = TextCatalogRegistry()
    keys: list[OwnerTextKey] = setup_keys()

    assert len(keys) == len(setup_texts())
    for language in CABINET_LANGUAGES:
        missing = set(registry.list_missing_keys(language)) & set(keys)
        assert missing == set(), language


def test_hebrew_and_german_are_drafts_the_others_reviewed() -> None:
    registry = TextCatalogRegistry()

    for key in setup_keys():
        for language in CABINET_LANGUAGES:
            status = registry.review_status(key, language)
            assert status is (
                TextReviewStatus.NEEDS_REVIEW
                if language in DRAFT_LANGUAGES
                else TextReviewStatus.REVIEWED
            ), (key, language)


def test_a_hebrew_or_german_cabinet_reads_its_own_language() -> None:
    resolver = LocalizedTextResolver()
    title = STEP_TITLES[SetupStepCode.TEST]

    english = resolver.resolve(title, LanguageTag("en"))
    hebrew = resolver.resolve(title, LanguageTag("he"))
    german = resolver.resolve(title, LanguageTag("de-AT"))

    assert str(english) == "Try your assistant"
    assert str(hebrew) == "נסו את העוזר שלכם"
    assert str(german) == "Testen Sie Ihren Assistenten"
    assert len({str(english), str(hebrew), str(german)}) == 3
