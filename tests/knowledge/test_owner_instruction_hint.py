"""
The profile wizard tells the owner what a rule and the tone may hold (the
one-line hint, in English and Italian): exactly the characters the save
refuses (`owner_instructions.REFUSAL_DETAIL`), and the leading #.
"""

import re
from pathlib import Path

import pytest

from app.utilities.knowledge.owner_instructions import REFUSAL_DETAIL

DICTIONARIES: Path = (
    Path(__file__).resolve().parents[2] / "web/src/i18n/messages/onboarding"
)
HINT: re.Pattern[str] = re.compile(r'^\s*instructionRule: "(.*)",$', re.MULTILINE)
REFUSED_CHARACTERS: str = REFUSAL_DETAIL.split("without ")[1].split(" characters")[0]


@pytest.mark.parametrize("language", ["en", "it"])
def test_the_wizard_names_the_characters_a_save_refuses(language: str) -> None:
    source: str = (DICTIONARIES / f"profileEdit.{language}.ts").read_text("utf-8")
    [hint] = HINT.findall(source)

    assert REFUSED_CHARACTERS == "< > [ ] { } `"
    assert REFUSED_CHARACTERS in hint
    assert "#" in hint
