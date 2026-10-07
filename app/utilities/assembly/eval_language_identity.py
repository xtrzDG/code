"""
The language-identity criterion of the evaluation harness: what each reply
reads as, not only which script it is written in.

The script check (`eval_scorers.score_language`) lets a Ukrainian reply to
a Russian customer through, or Portuguese for Spanish: both are written in
the same letters. Here every written reply (without the server's AI
disclosure) is read by the platform's own any-language detector
(`detect_any_language`, which reads ~55 languages and transliterations)
with the scenario's language as the only one it prefers on a tie, so a
reply fails only when another language reads clearly better. A reply that
tells too little ("OK!", a price) is undetermined and passes.
"""

from collections.abc import Sequence

from app.schemas.constants.evaluations import EvalCriterion
from app.schemas.dto.assistants.autotest_runs import AutotestScenario
from app.schemas.dto.conversations import AssistantReply
from app.schemas.dto.evaluations import LanguageIdentityScore, ReplyLanguageReading
from app.schemas.dto.language_detection import DetectedLanguage
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.assembly.autotest_evaluation import read_model_text
from app.utilities.assembly.eval_text_scorers import result
from app.utilities.conversations.any_language_detection import (
    LanguageContext,
    detect_any_language,
)
from app.utilities.localization.language_tags import base_language_code


def read_reply_language(text: str, expected: LanguageTag) -> LanguageTag | None:
    """
    The language `text` reads as; None when it tells too little. The
    expected language wins a tie and nothing else is preferred: no kept
    language, no other business language.
    """

    detected: DetectedLanguage = detect_any_language(
        text,
        LanguageContext(
            version_languages=(expected,),
            default_language=expected,
            kept_language=None,
        ),
    )
    return detected.language if detected.is_read_from_text else None


def score_language_identity(
    scenario: AutotestScenario, replies: Sequence[AssistantReply]
) -> LanguageIdentityScore:
    """Every written reply reads as the scenario's base language."""

    expected_base: str = base_language_code(scenario.language)
    written: list[AssistantReply] = [reply for reply in replies if reply.text]
    notes: list[str] = [] if written else ["The assistant wrote no reply."]
    readings: list[ReplyLanguageReading] = []
    for number, reply in enumerate(written, start=1):
        detected: LanguageTag | None = read_reply_language(
            read_model_text(reply), scenario.language
        )
        readings.append(ReplyLanguageReading(detected_language=detected))
        if detected is not None and base_language_code(detected) != expected_base:
            notes.append(
                f"Reply {number} reads as {detected}, not {scenario.language} "
                f"({scenario.language_name})."
            )

    return LanguageIdentityScore(
        result=result(EvalCriterion.LANGUAGE_IDENTITY, notes), readings=readings
    )
