"""Reading the judge's answer: JSON, prose, fences, numbers, bad verdicts and notes."""

import json

import pytest

from app.schemas.constants.assistants import JudgeCriterion
from app.utilities.assembly.judge_verdicts import parse_judge_verdict
from tests.assembly.judge_helpers import PERFECT


def test_plain_json_verdict_is_read() -> None:
    verdict = parse_judge_verdict(
        json.dumps({"scores": {**PERFECT, "handoff": 3}, "notes": ["Late handoff."]})
    )

    assert verdict is not None
    assert [int(score.score) for score in verdict.scores] == [5, 5, 5, 3, 5]
    assert [score.criterion for score in verdict.scores] == list(JudgeCriterion)
    assert verdict.notes == ["Late handoff."]


def test_verdict_inside_prose_and_code_fences_is_read() -> None:
    answer = (
        "Here is my evaluation:\n```json\n"
        + json.dumps({"scores": PERFECT, "notes": "All good."})
        + "\n```\nThanks!"
    )

    verdict = parse_judge_verdict(answer)

    assert verdict is not None
    assert verdict.notes == ["All good."]


def test_numbers_as_floats_or_digit_strings_are_accepted() -> None:
    verdict = parse_judge_verdict(
        json.dumps(
            {
                "scores": {
                    **PERFECT,
                    "language": 4.0,
                    "facts_and_prices": " 3 ",
                }
            }
        )
    )

    assert verdict is not None
    assert int(verdict.scores[0].score) == 3
    assert int(verdict.scores[4].score) == 4
    assert verdict.notes == []


@pytest.mark.parametrize(
    "answer",
    [
        None,
        "",
        "I think the assistant did great.",
        "{not json}",
        json.dumps([PERFECT]),
        json.dumps({"notes": ["no scores"]}),
        json.dumps({"scores": "5"}),
        json.dumps({"scores": {**PERFECT, "language": 6}}),
        json.dumps({"scores": {**PERFECT, "handoff": 0}}),
        json.dumps({"scores": {**PERFECT, "handoff": 4.5}}),
        json.dumps({"scores": {**PERFECT, "handoff": True}}),
        json.dumps({"scores": {**PERFECT, "handoff": "good"}}),
        json.dumps({"scores": {"facts_and_prices": 5, "language": 5}}),
    ],
)
def test_unreadable_verdicts_are_rejected(answer: str | None) -> None:
    assert parse_judge_verdict(answer) is None


def test_notes_are_trimmed_and_capped() -> None:
    verdict = parse_judge_verdict(
        json.dumps(
            {
                "scores": PERFECT,
                "notes": ["  first  ", 42, "", *[f"note {n}" for n in range(20)]],
            }
        )
    )

    assert verdict is not None
    assert verdict.notes[0] == "first"
    assert len(verdict.notes) == 10
    long_note = parse_judge_verdict(json.dumps({"scores": PERFECT, "notes": "x" * 900}))
    assert long_note is not None
    assert len(long_note.notes[0]) == 500
