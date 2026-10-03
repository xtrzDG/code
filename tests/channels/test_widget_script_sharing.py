"""The widget script's starters, "Talk to a person", footer and page mode."""

import json
import re
import shutil
import subprocess

import pytest

from app.gateways.http.widget_handoff_routes import WIDGET_HANDOFF_PATH
from tests.channels.widget_script_source import SCRIPT_SOURCE


def read_script_constant(name: str) -> str:
    match = re.search(rf'var {name} = "([^"]*)";', SCRIPT_SOURCE)
    assert match is not None, name
    return match.group(1)


def extract_function(name: str) -> str:
    match = re.search(rf"\n  function {name}\(.*?\n  \}}\n", SCRIPT_SOURCE, re.S)
    assert match is not None, name
    return match.group(0)


def run_in_node(functions: list[str], call: str) -> object:
    node = shutil.which("node")
    assert node is not None
    program: str = (
        "var MAX_STARTERS = 3;\n"
        + "".join(extract_function(name) for name in functions)
        + f"\nconsole.log(JSON.stringify({call}));"
    )
    result = subprocess.run(
        [node, "-e", program], capture_output=True, text=True, timeout=60, check=False
    )
    assert result.returncode == 0, result.stderr
    parsed: object = json.loads(result.stdout)
    return parsed


def test_the_handoff_path_is_the_one_the_api_serves() -> None:
    assert read_script_constant("HANDOFF_PATH") == WIDGET_HANDOFF_PATH
    assert read_script_constant("PAGE_MODE") == "page"


def test_links_of_the_config_are_checked_before_they_are_shown() -> None:
    # The footer and the page's other channels only show http(s) and tel:
    # links; anything else (javascript:) never becomes an href.
    assert "WEB_LINK_PATTERN.test(config.privacy_url)" in SCRIPT_SOURCE
    assert "CONTACT_LINK_PATTERN.test(link.url)" in SCRIPT_SOURCE
    assert 'rel = "noopener noreferrer"' in SCRIPT_SOURCE


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
class TestStarterQuestions:
    FUNCTIONS = ["starterQuestions", "isSameLanguage", "baseLanguage"]
    CONFIG = {
        "starter_questions": [
            {"language": "ru", "text": "Есть парковка?"},
            {"language": "en", "text": "Parking?"},
            {"language": "en", "text": "Delivery?"},
            {"language": "en", "text": "Cards?"},
            {"language": "en", "text": "Kids?"},
            {"language": "pt-BR", "text": "Estacionamento?"},
        ]
    }

    def starters(self, tag: str) -> object:
        return run_in_node(
            self.FUNCTIONS,
            f"starterQuestions({json.dumps(self.CONFIG)}, {json.dumps(tag)})",
        )

    def test_at_most_three_in_the_interface_language(self) -> None:
        assert self.starters("en") == ["Parking?", "Delivery?", "Cards?"]
        assert self.starters("ru") == ["Есть парковка?"]

    def test_a_regional_tag_finds_its_base_language(self) -> None:
        assert self.starters("en-GB") == ["Parking?", "Delivery?", "Cards?"]
        assert self.starters("pt") == ["Estacionamento?"]

    def test_no_questions_in_other_languages(self) -> None:
        assert self.starters("ka") == []
        assert run_in_node(self.FUNCTIONS, "starterQuestions({}, 'en')") == []
