"""
The semantic judge of an owner check that must (not) mention something:
the word rules (`owner_check_evaluation`) see "собаки разрешены" and
"с питомцами можно" as different answers, a language model does not.

The judge gets the customer's question, the assistant's answers and what
they must (or must not) convey, and answers `{"conveys": true|false,
"note": "..."}` with the note in the owner's language. Anything else is
unreadable, and the rules decide alone.
"""

from collections.abc import Sequence

from app.schemas.constants.assistants import (
    AutotestExpectation,
    LlmProvider,
)
from app.schemas.dto.assistants.autotest_runs import OwnerCheckSpec
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import JudgeNote
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.assembly.judge_verdicts import (
    MAX_JUDGE_NOTE_LENGTH,
    extract_json_object,
)
from app.utilities.conversations.llm_models import resolve_llm_provider

OWNER_CHECK_JUDGE_OPENING: str = (
    "You check one answer of an AI assistant that talks to the customers of "
    "a business against what its owner expects."
)
OWNER_CHECK_JUDGE_PROMPT: str = "\n".join(
    [
        f"{OWNER_CHECK_JUDGE_OPENING} You get the customer's question, the "
        "assistant's answers and a phrase.",
        "Decide whether the answers convey the meaning of the phrase, in any "
        "language and in any words: a synonym, a paraphrase or a translation "
        "counts, a mere mention of a different thing does not.",
        "Reply with JSON only, without markdown, in exactly this shape: "
        '{"conveys": true, "note": "one short sentence why"}',
    ]
)
# Judges of these providers read meaning; the scripted rehearsal model of
# development and end-to-end servers does not, so the rules decide there.
SEMANTIC_JUDGE_PROVIDERS: frozenset[LlmProvider] = frozenset(
    {LlmProvider.OPENAI, LlmProvider.ANTHROPIC}
)
TEXT_EXPECTATIONS: frozenset[AutotestExpectation] = frozenset(
    {AutotestExpectation.MUST_MENTION, AutotestExpectation.MUST_NOT_MENTION}
)


def can_judge_meaning(judge_model_id: LlmModelId) -> bool:
    """Whether the judge model reads meaning (a real provider's model)."""

    return resolve_llm_provider(judge_model_id) in SEMANTIC_JUDGE_PROVIDERS


def build_owner_check_judge_text(
    check: OwnerCheckSpec,
    answers: Sequence[str],
    notes_language: LanguageTag,
) -> str:
    """The judge's user turn: the question, the answers and the phrase."""

    numbered: list[str] = [
        f"{number}. {answer}" for number, answer in enumerate(answers, start=1)
    ]
    return "\n".join(
        [
            f"Customer's question: {check.question}",
            "Assistant's answers:",
            *numbered,
            f"Phrase: {check.expected_text or ''}",
            f"Write the note in the language with the tag {notes_language}.",
        ]
    )


def parse_owner_check_verdict(
    answer_text: str | None,
) -> tuple[bool, JudgeNote | None] | None:
    """
    Whether the answers convey the phrase and the judge's note, or None
    when the answer cannot be read.
    """

    if answer_text is None:
        return None

    payload: dict[str, object] | None = extract_json_object(answer_text)
    if payload is None:
        return None

    conveys: object = payload.get("conveys")
    if not isinstance(conveys, bool):
        return None

    raw_note: object = payload.get("note")
    note: str = raw_note.strip() if isinstance(raw_note, str) else ""
    return (
        conveys,
        JudgeNote(note[:MAX_JUDGE_NOTE_LENGTH]) if note else None,
    )
