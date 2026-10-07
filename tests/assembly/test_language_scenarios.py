"""
The language autotests: a customer who writes a language the business did
not list, one who types a business language in Latin letters, and the
deterministic check that the AI disclosure came in the customer's language.
"""

from app.schemas.constants.assistants import AutotestCheckCode, AutotestScenarioKind
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.utilities.assembly.assistant_tools import select_assistant_tools
from app.utilities.assembly.autotest_evaluation import check_conversation
from app.utilities.assembly.autotest_prompts import (
    TRANSLITERATION_NOTE,
    build_customer_persona_prompt,
)
from app.utilities.assembly.autotest_scenarios import (
    RED_TEAM_SCENARIO_KINDS,
    list_applicable_kinds,
)
from app.utilities.assembly.language_scenarios import (
    choose_foreign_languages,
    choose_transliterated_languages,
)
from tests.assembly.autotest_scripts import build_reply
from tests.assembly.judge_helpers import scenario

LANGUAGE_KINDS: list[AutotestScenarioKind] = [
    AutotestScenarioKind.FOREIGN_LANGUAGE,
    AutotestScenarioKind.TRANSLITERATED,
]
HEBREW_DISCLOSURE: str = "שלום! אני עוזר ה-AI של Mtsvane Ezo."


def tags(*codes: str) -> list[LanguageTag]:
    return [LanguageTag(code) for code in codes]


def test_foreign_languages_are_one_in_a_new_script_and_one_in_latin() -> None:
    assert choose_foreign_languages(tags("ka", "ru", "en")) == tags("he", "de")
    assert choose_foreign_languages(tags("he", "ar", "en", "ru")) == tags("hy", "de")
    assert choose_foreign_languages(tags("de", "en")) == tags("he", "fr")


def test_transliteration_is_planned_for_languages_typed_in_latin_letters() -> None:
    assert choose_transliterated_languages(tags("ka", "en", "ru")) == tags("ka", "ru")
    assert choose_transliterated_languages(tags("uk", "hy", "he")) == tags(
        "uk", "hy", "he"
    )
    assert choose_transliterated_languages(tags("en", "de", "ar")) == []


def test_the_transliteration_kind_applies_only_to_such_languages() -> None:
    tools = select_assistant_tools(takes_bookings=True, has_links=True)

    georgian = list_applicable_kinds(LANGUAGE_KINDS, tools, tags("ka", "en"))
    german = list_applicable_kinds(LANGUAGE_KINDS, tools, tags("de", "en"))

    assert georgian == [*LANGUAGE_KINDS, *RED_TEAM_SCENARIO_KINDS]
    assert german == [AutotestScenarioKind.FOREIGN_LANGUAGE, *RED_TEAM_SCENARIO_KINDS]


def test_the_ai_customer_is_told_how_to_write() -> None:
    transliterated = build_customer_persona_prompt(
        "Mtsvane Ezo",
        scenario(AutotestScenarioKind.TRANSLITERATED),
        E164PhoneNumber("+995555123456"),
        [],
    )
    foreign = build_customer_persona_prompt(
        "Mtsvane Ezo",
        scenario(AutotestScenarioKind.FOREIGN_LANGUAGE, "he", "Hebr", "Hebrew"),
        None,
        [],
    )

    assert TRANSLITERATION_NOTE in str(transliterated)
    assert "only language you speak" in str(foreign)
    assert TRANSLITERATION_NOTE not in str(foreign)


def test_a_disclosure_in_the_customer_language_passes() -> None:
    hebrew = scenario(AutotestScenarioKind.FOREIGN_LANGUAGE, "he", "Hebr", "Hebrew")
    reply = build_reply("he", text=f"{HEBREW_DISCLOSURE}\nכן, אנחנו פתוחים.")
    disclosed = reply.model_copy(
        update={"disclosure_text": MessageText(HEBREW_DISCLOSURE)}
    )

    assert check_conversation(hebrew, [disclosed], "Mtsvane Ezo") == []


def test_a_disclosure_in_another_language_fails() -> None:
    hebrew = scenario(AutotestScenarioKind.FOREIGN_LANGUAGE, "he", "Hebr", "Hebrew")
    georgian_disclosure = "გამარჯობა! მე ვარ Mtsvane Ezo-ის AI-ასისტენტი."
    reply = build_reply("ka", text=f"{georgian_disclosure}\nכן.").model_copy(
        update={"disclosure_text": MessageText(georgian_disclosure)}
    )

    failures = check_conversation(hebrew, [reply], "Mtsvane Ezo")

    assert [failure.code for failure in failures] == [
        AutotestCheckCode.WRONG_DISCLOSURE_LANGUAGE
    ]
    assert "not in Hebrew (he)" in str(failures[0].note)


def test_a_disclosure_in_the_wrong_script_fails_even_with_the_right_tag() -> None:
    hebrew = scenario(AutotestScenarioKind.FOREIGN_LANGUAGE, "he", "Hebr", "Hebrew")
    english = "Hello! I am the AI assistant of Mtsvane Ezo."
    reply = build_reply("he", text=f"{english}\nכן.").model_copy(
        update={"disclosure_text": MessageText(english)}
    )

    assert [failure.code for failure in check_conversation(hebrew, [reply])] == [
        AutotestCheckCode.WRONG_DISCLOSURE_LANGUAGE
    ]


def test_no_disclosure_means_nothing_to_check() -> None:
    hebrew = scenario(AutotestScenarioKind.FOREIGN_LANGUAGE, "he", "Hebr", "Hebrew")

    assert check_conversation(hebrew, [build_reply("he", text="כן.")]) == []
