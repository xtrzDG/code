"""
The language-identity criterion reads each reply with the platform's
any-language detector: a reply in the scenario's script but another
language fails, a reply that tells too little passes undetermined.
"""

from app.schemas.constants.evaluations import EvalCriterion
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.assembly.eval_language_identity import (
    read_reply_language,
    score_language_identity,
)
from tests.evals.eval_builders import reply, scenario

UKRAINIAN_REPLY: str = (
    "Добрий день! Стандартний двомісний номер коштує 180 ларі. Чим ще можу допомогти?"
)
PORTUGUESE_REPLY: str = (
    "Olá! Um corte de cabelo feminino custa 60 laris. "
    "Posso ajudar com mais alguma coisa? Obrigado pela mensagem."
)


def test_a_reply_in_the_scenario_language_passes() -> None:
    score = score_language_identity(
        scenario("ru"),
        [reply("Стандартный двухместный номер стоит 180 лари. Чем ещё помочь?")],
    )

    assert score.result.criterion is EvalCriterion.LANGUAGE_IDENTITY
    assert score.result.is_passed
    assert [reading.detected_language for reading in score.readings] == ["ru"]


def test_ukrainian_for_a_russian_customer_fails_although_the_script_matches() -> None:
    score = score_language_identity(scenario("ru"), [reply(UKRAINIAN_REPLY)])

    assert not score.result.is_passed
    assert [str(note) for note in score.result.notes] == [
        "Reply 1 reads as uk, not ru (Russian)."
    ]


def test_portuguese_for_a_spanish_customer_fails() -> None:
    score = score_language_identity(scenario("es"), [reply(PORTUGUESE_REPLY)])

    assert not score.result.is_passed
    assert score.readings[0].detected_language == "pt"


def test_a_reply_that_tells_too_little_is_undetermined_and_passes() -> None:
    score = score_language_identity(scenario("ka"), [reply("OK!")])

    assert score.result.is_passed
    assert score.readings[0].detected_language is None


def test_the_server_disclosure_is_not_read() -> None:
    score = score_language_identity(
        scenario("en"),
        [
            reply(
                "The standard double room costs 180 GEL. Anything else?",
                disclosure="Здравствуйте! Я AI-ассистент отеля.",
            )
        ],
    )

    assert score.result.is_passed
    assert score.readings[0].detected_language == "en"


def test_no_written_reply_fails() -> None:
    score = score_language_identity(scenario("en"), [reply(None)])

    assert [str(note) for note in score.result.notes] == [
        "The assistant wrote no reply."
    ]
    assert score.readings == []


def test_the_expected_language_wins_only_a_tie() -> None:
    assert read_reply_language(UKRAINIAN_REPLY, LanguageTag("ru")) == "uk"
    assert read_reply_language("Merci beaucoup !", LanguageTag("fr")) == "fr"
