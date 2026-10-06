"""The widget script's chips for the options of the assistant's last reply."""

import json
import re
import shutil
import subprocess

import pytest

from app.schemas.domain.reply_choices import MAX_CHOICES
from app.schemas.typings.conversations.constrained_strings import ChoiceLabel
from tests.channels.widget_script_source import SCRIPT_SOURCE


def read_script_number(name: str) -> int:
    match = re.search(rf"var {name} = ([0-9]+);", SCRIPT_SOURCE)
    assert match is not None, name
    return int(match.group(1))


def extract_function(name: str) -> str:
    """A function of the script, up to the brace at its own indentation."""

    match = re.search(rf"\n( +)function {name}\(.*?\n\1\}}\n", SCRIPT_SOURCE, re.S)
    assert match is not None, name
    return match.group(0)


def run_in_node(program: str) -> object:
    node = shutil.which("node")
    assert node is not None
    result = subprocess.run(
        [node, "-e", program], capture_output=True, text=True, timeout=60, check=False
    )
    assert result.returncode == 0, result.stderr
    parsed: object = json.loads(result.stdout)
    return parsed


def test_the_limits_are_the_ones_the_api_keeps() -> None:
    assert read_script_number("MAX_CHOICES") == MAX_CHOICES
    assert read_script_number("MAX_CHOICE_LENGTH") == ChoiceLabel.max_length


def test_options_come_from_polling_and_survive_a_reload() -> None:
    # The stored message (polling) brings the options, also for the draft
    # an answer event showed first; the history keeps them.
    assert SCRIPT_SOURCE.count("readChoices(message.choices)") == 2
    assert "choices: readChoices(item.choices)" in SCRIPT_SOURCE
    assert "choices: item.choices && item.choices.length" in SCRIPT_SOURCE


def test_a_tap_sends_the_option_as_the_visitors_message() -> None:
    render: str = extract_function("renderActions")
    assert '"aw-starter aw-choice"' in render
    assert "input.value = question;" in render
    assert "submit();" in render
    # Options are text, never markup.
    assert "chip.textContent = question;" in render


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
class TestReadChoices:
    def read(self, value: object) -> object:
        return run_in_node(
            f"var MAX_CHOICES = {MAX_CHOICES};\n"
            f"var MAX_CHOICE_LENGTH = {ChoiceLabel.max_length};\n"
            + extract_function("readChoices")
            + f"\nconsole.log(JSON.stringify(readChoices({json.dumps(value)})));"
        )

    def test_keeps_short_texts_in_order(self) -> None:
        assert self.read(["18:00", "19:30"]) == ["18:00", "19:30"]

    def test_drops_what_the_api_never_sends(self) -> None:
        assert self.read(["ok", "", "   ", 7, None, "x" * 21, {"a": 1}]) == ["ok"]
        assert self.read(None) == []
        assert self.read("18:00") == []

    def test_keeps_at_most_ten(self) -> None:
        options = [f"Option {number}" for number in range(12)]
        assert self.read(options) == options[:MAX_CHOICES]


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
class TestOfferedChoices:
    def offered(self, history: list[dict[str, object]], handed_off: bool) -> object:
        state = {"history": history, "isHandedOff": handed_off}
        return run_in_node(
            f"var state = {json.dumps(state)};\n"
            + extract_function("offeredChoices")
            + "\nconsole.log(JSON.stringify(offeredChoices()));"
        )

    def test_the_last_assistant_reply_offers_its_options(self) -> None:
        history: list[dict[str, object]] = [
            {"role": "visitor", "text": "A table for two?"},
            {"role": "assistant", "text": "Which time?", "choices": ["18:00", "19:30"]},
        ]
        assert self.offered(history, handed_off=False) == ["18:00", "19:30"]

    def test_a_notice_after_the_reply_keeps_them(self) -> None:
        history: list[dict[str, object]] = [
            {"role": "assistant", "text": "Which time?", "choices": ["18:00", "19:30"]},
            {"role": "notice", "key": "newChat"},
        ]
        assert self.offered(history, handed_off=False) == ["18:00", "19:30"]

    def test_none_once_the_visitor_wrote_or_staff_took_over(self) -> None:
        offered: list[dict[str, object]] = [
            {"role": "assistant", "text": "Which time?", "choices": ["18:00", "19:30"]}
        ]
        answered: list[dict[str, object]] = [
            *offered,
            {"role": "visitor", "text": "18:00"},
        ]
        assert self.offered(answered, handed_off=False) == []
        assert self.offered(offered, handed_off=True) == []
        staff: list[dict[str, object]] = [
            *offered,
            {"role": "staff", "text": "Hi, Dana here"},
        ]
        assert self.offered(staff, handed_off=False) == []
