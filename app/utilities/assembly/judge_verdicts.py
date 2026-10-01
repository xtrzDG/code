"""
Defensive parsing of the judge's answer.

The judge is asked for `{"scores": {<criterion>: 1..5, ...}, "notes": [...]}`.
Models sometimes wrap JSON in prose or code fences, so the outermost object
is cut out first. Anything else (a missing criterion, a score outside 1..5,
no JSON object) makes the verdict unreadable and the scenario ERRORED.
"""

import json
from typing import cast

from app.schemas.constants.assistants import JudgeCriterion
from app.schemas.domain.assistants import JudgeCriterionScore
from app.schemas.dto.assistants import JudgeVerdict
from app.schemas.typings.assistants.constrained_integers import JudgeScore
from app.schemas.typings.assistants.strings import JudgeNote

MIN_JUDGE_SCORE: int = 1
MAX_JUDGE_SCORE: int = 5
MAX_JUDGE_NOTES: int = 10
MAX_JUDGE_NOTE_LENGTH: int = 500


def parse_judge_verdict(answer_text: str | None) -> JudgeVerdict | None:
    """The verdict in the judge's answer, or None when it cannot be read."""

    if answer_text is None:
        return None

    payload: dict[str, object] | None = extract_json_object(answer_text)
    if payload is None:
        return None

    raw_scores: object = payload.get("scores")
    if not isinstance(raw_scores, dict):
        return None

    score_mapping: dict[str, object] = {
        str(key): value for key, value in cast(dict[object, object], raw_scores).items()
    }
    scores: list[JudgeCriterionScore] = []
    for criterion in JudgeCriterion:
        score: int | None = read_score(score_mapping.get(criterion.value))
        if score is None:
            return None

        scores.append(JudgeCriterionScore(criterion=criterion, score=JudgeScore(score)))

    return JudgeVerdict(scores=scores, notes=read_notes(payload.get("notes")))


def extract_json_object(text: str) -> dict[str, object] | None:
    """The outermost JSON object in a text (prose and code fences ignored)."""

    start: int = text.find("{")
    end: int = text.rfind("}")
    if start == -1 or end <= start:
        return None

    try:
        decoded: object = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None

    if not isinstance(decoded, dict):
        return None

    return {
        str(key): value for key, value in cast(dict[object, object], decoded).items()
    }


def read_score(raw_score: object) -> int | None:
    """A whole score from 1 to 5 given as a number or a digit string."""

    candidate: int
    if isinstance(raw_score, bool):
        return None

    if isinstance(raw_score, int):
        candidate = raw_score
    elif isinstance(raw_score, float) and raw_score.is_integer():
        candidate = int(raw_score)
    elif isinstance(raw_score, str) and raw_score.strip().isdecimal():
        candidate = int(raw_score.strip())
    else:
        return None

    if not MIN_JUDGE_SCORE <= candidate <= MAX_JUDGE_SCORE:
        return None

    return candidate


def read_notes(raw_notes: object) -> list[JudgeNote]:
    """Notes as a list of short texts; a single string counts as one note."""

    raw_items: list[object]
    if isinstance(raw_notes, str):
        raw_items = [raw_notes]
    elif isinstance(raw_notes, list):
        raw_items = list(cast(list[object], raw_notes))
    else:
        return []

    notes: list[JudgeNote] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, str) or raw_item.strip() == "":
            continue

        notes.append(JudgeNote(raw_item.strip()[:MAX_JUDGE_NOTE_LENGTH]))
        if len(notes) == MAX_JUDGE_NOTES:
            break

    return notes
