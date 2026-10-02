"""The widget script's texts, greetings, colours and language picker."""

import json
import re
import shutil
import subprocess

import pytest

from app.registries.localization.curated_country_languages import (
    CURATED_CUSTOMER_LANGUAGES,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.channels.widget_texts import WIDGET_GREETING, build_widget_greeting
from app.utilities.localization.language_tags import base_language_code
from tests.channels.widget_script_source import SCRIPT_SOURCE


def read_script_texts() -> dict[str, set[str]]:
    """The interface languages of the script and the keys each one has."""

    block: str = SCRIPT_SOURCE[SCRIPT_SOURCE.index("var TEXTS = {") :]
    block = block[: block.index("\n  };")]
    texts: dict[str, set[str]] = {}
    for match in re.finditer(r"\n    ([a-z]+): \{(.*?)\n    \}", block, re.S):
        texts[match.group(1)] = set(re.findall(r"\n      ([A-Za-z]+):", match.group(2)))
    return texts


def read_script_greetings() -> dict[str, str]:
    """The script's own greeting in each of its interface languages."""

    block: str = SCRIPT_SOURCE[SCRIPT_SOURCE.index("var TEXTS = {") :]
    block = block[: block.index("\n  };")]
    greetings: dict[str, str] = {}
    for match in re.finditer(r"\n    ([a-z]+): \{(.*?)\n    \}", block, re.S):
        greeting = re.search(r'\n      greeting: ("(?:[^"\\]|\\.)*")', match.group(2))
        assert greeting is not None, match.group(1)
        greetings[match.group(1)] = json.loads(greeting.group(1))
    return greetings


def run_script_function(function_name: str, call: str) -> str:
    """Run one function of the script in node and return what it prints."""

    node = shutil.which("node")
    assert node is not None
    match = re.search(
        rf"\n  function {function_name}\(.*?\n  \}}\n", SCRIPT_SOURCE, re.S
    )
    assert match is not None, function_name
    result = subprocess.run(
        [node, "-e", f"{match.group(0)}\nconsole.log({call});"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


class TestWidgetTexts:
    def test_every_curated_customer_language_has_complete_interface_texts(
        self,
    ) -> None:
        texts = read_script_texts()
        english_keys = texts["en"]
        curated = {
            base_language_code(tag).lower()
            for tags in CURATED_CUSTOMER_LANGUAGES.values()
            for tag in tags
        }

        assert sorted(code for code in curated if code not in texts) == []
        for code in curated:
            assert texts[code] == english_keys, code

    def test_the_api_greets_in_every_interface_language_of_the_script(
        self,
    ) -> None:
        script_greetings = read_script_greetings()
        api_languages = {str(tag) for tag in WIDGET_GREETING.values}

        assert api_languages == set(script_greetings)
        for language, script_greeting in script_greetings.items():
            # The API's greeting (sent with the widget config) wins over the
            # script's own one, so both say the same thing.
            assert build_widget_greeting(LanguageTag(language), "{business}") == (
                script_greeting
            ), language


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
class TestWidgetColours:
    @pytest.mark.parametrize(
        ("accent", "text_colour"),
        [
            # Mid-tone brand colours: dark text reads better than white.
            ("#f59e0b", "#111827"),
            ("#22c55e", "#111827"),
            ("#06b6d4", "#111827"),
            ("#f97316", "#111827"),
            ("#fde047", "#111827"),
            # Dark colours and the cabinet's presets keep white text.
            ("#4f46e5", "#ffffff"),
            ("#111827", "#ffffff"),
            ("#1d4ed8", "#ffffff"),
            ("#15803d", "#ffffff"),
        ],
    )
    def test_text_on_the_accent_takes_the_higher_contrast(
        self, accent: str, text_colour: str
    ) -> None:
        assert (
            run_script_function("readableTextColor", f'readableTextColor("{accent}")')
            == text_colour
        )


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
class TestWidgetLanguagePicker:
    @pytest.mark.parametrize(
        ("language", "label"),
        [
            ('{tag: "ru", native_name: "русский"}', "Русский"),
            ('{tag: "de", native_name: "Deutsch"}', "Deutsch"),
            # Georgian has no capitals; uppercasing would give Mtavruli.
            ('{tag: "ka", native_name: "ქართული"}', "ქართული"),
            ('{tag: "he", native_name: "עברית"}', "עברית"),
            ('{tag: "xx"}', "Xx"),
        ],
    )
    def test_languages_are_named_with_a_capital_where_the_script_has_one(
        self, language: str, label: str
    ) -> None:
        assert run_script_function("pickerLabel", f"pickerLabel({language})") == label
