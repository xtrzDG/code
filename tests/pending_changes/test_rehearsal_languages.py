"""
The rehearsal model (LLM_PROVIDER=scripted) in the language autotests: it
answers in the language the platform read the customer in, and its AI
customer types in Latin letters when the scenario asks for it.
"""

from app.adapters.llm.llm_payloads import build_user_text_payload
from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.dto.assistants.autotest_runs import AutotestScenario
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    ScriptCode,
)
from app.schemas.typings.localization.strings import LanguageDisplayName
from app.utilities.assembly.autotest_prompts import build_customer_persona_prompt
from app.utilities.assembly.autotest_scenarios import build_goal, build_scenario_key
from app.utilities.conversations.customer_text_fencing import fence_customer_text
from app.utilities.conversations.language_detector import LanguageDetector
from app.utilities.conversations.turn_context import CUSTOMER_HEADER
from app.utilities.llm_rehearsal.assistant_phrases import (
    ASSISTANT_PHRASES,
    RehearsalReply,
)
from app.utilities.llm_rehearsal.customer_phrases import TRANSLITERATED_PHRASES
from app.utilities.llm_rehearsal.rehearsal_reading import read_reply_language
from tests.pending_changes.test_rehearsal_model import ASSISTANT_PROMPT, ask


def platform_turn(reply_language_line: str, text: str) -> str:
    return str(
        build_user_text_payload(
            MessageText(
                f"Channel: owner_test.\n{reply_language_line}\n"
                f"{CUSTOMER_HEADER}\n{fence_customer_text(text, 'k7')}"
            )
        )
    )


def test_the_assistant_answers_in_the_language_the_platform_read() -> None:
    transcript = [
        platform_turn(
            "Reply language: Georgian (ka). The customer types it in Latin "
            "letters; reply in Georgian script unless they ask for Latin letters.",
            "gamarjoba, kitxva makvs",
        )
    ]

    reply = ask(str(ASSISTANT_PROMPT), transcript)

    assert read_reply_language(transcript) == "ka"
    assert str(reply.text) == ASSISTANT_PHRASES["ka"][RehearsalReply.ANSWER]


def test_without_the_line_the_assistant_reads_the_words_itself() -> None:
    transcript = [str(build_user_text_payload(MessageText("שלום, יש לי שאלה")))]

    reply = ask(str(ASSISTANT_PROMPT), transcript)

    assert read_reply_language(transcript) is None
    assert str(reply.text) == ASSISTANT_PHRASES["he"][RehearsalReply.ANSWER]


def test_the_customer_of_a_transliteration_scenario_types_latin_letters() -> None:
    scenario = AutotestScenario(
        key=build_scenario_key(AutotestScenarioKind.TRANSLITERATED, LanguageTag("ru")),
        kind=AutotestScenarioKind.TRANSLITERATED,
        language=LanguageTag("ru"),
        language_name=LanguageDisplayName("Russian"),
        language_script=ScriptCode("Cyrl"),
        goal=build_goal(AutotestScenarioKind.TRANSLITERATED, "table", 2),
    )

    opening = ask(str(build_customer_persona_prompt("Sakhli", scenario, None, [])), [])

    assert str(opening.text) == TRANSLITERATED_PHRASES["ru"]


def test_every_transliterated_phrase_is_read_in_its_language() -> None:
    detector = LanguageDetector()
    business = [LanguageTag("ka"), LanguageTag("ru"), LanguageTag("en")]

    for language, phrase in TRANSLITERATED_PHRASES.items():
        detected = detector.detect_any(
            MessageText(phrase), business, LanguageTag("ka"), None, None
        )

        assert (detected.language, detected.script_hint) == (language, "Latn")
