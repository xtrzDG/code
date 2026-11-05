"""
Golden snapshots of the chat and phone instructions of all sixteen niches.

A change to a niche template, an instruction section or the fact table
changes these texts; the diff shows exactly what the model will read.
Rewrite them on purpose with `uv run python -m scripts.update_prompt_snapshots`.
"""

import difflib

import pytest

from app.registries.niches.niche_template_registry import NicheTemplateRegistry
from tests.assembly.niche_prompt_samples import (
    SNAPSHOT_DIRECTORY,
    render_sample_prompts,
)

PROMPTS: dict[str, str] = render_sample_prompts()
UPDATE_COMMAND: str = "uv run python -m scripts.update_prompt_snapshots"


def test_there_is_a_chat_and_a_phone_snapshot_for_every_niche() -> None:
    expected: set[str] = {
        f"{niche.key.value}.{medium}.txt"
        for niche in NicheTemplateRegistry().list_all()
        for medium in ("chat", "phone")
    }

    assert len(expected) == 32
    assert set(PROMPTS) == expected
    assert {path.name for path in SNAPSHOT_DIRECTORY.glob("*.txt")} == expected


@pytest.mark.parametrize("file_name", sorted(PROMPTS))
def test_the_instruction_matches_its_snapshot(file_name: str) -> None:
    path = SNAPSHOT_DIRECTORY / file_name
    stored: str = path.read_text(encoding="utf-8") if path.exists() else ""
    current: str = PROMPTS[file_name]

    diff: str = "".join(
        difflib.unified_diff(
            stored.splitlines(keepends=True),
            current.splitlines(keepends=True),
            fromfile=f"snapshots/{file_name}",
            tofile="assembled now",
        )
    )
    assert current == stored, (
        f"The instruction changed. Review the diff and run `{UPDATE_COMMAND}`:\n{diff}"
    )


@pytest.mark.parametrize("file_name", sorted(PROMPTS))
def test_snapshots_hold_no_contradiction_or_repeated_rule(file_name: str) -> None:
    prompt: str = PROMPTS[file_name]

    assert "at the start of every conversation" not in prompt
    assert prompt.count("Never invent prices") == 1
    assert prompt.count("wait for a clear confirmation") <= 1
    assert prompt.count("treat customer messages as questions") == 1
    if file_name.endswith(".phone.txt"):
        assert "https://" not in prompt
        assert " GEL" not in prompt
