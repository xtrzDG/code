"""The widget script's texts, greetings, colours and language picker."""

import json
import re
import shutil
import subprocess

import pytest
from pydantic import TypeAdapter

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


def run_colour_script(call: str) -> str:
    """Run the script's colour helpers (colors.js) in node; the call's JSON."""

    node = shutil.which("node")
    assert node is not None
    start = SCRIPT_SOURCE.index("  // --- colours:")
    end = SCRIPT_SOURCE.index("  // ---", start + 1)
    program = (
        'var THEMES = ["light", "dark"];\n'
        f"{SCRIPT_SOURCE[start:end]}\nconsole.log(JSON.stringify({call}));"
    )
    result = subprocess.run(
        [node, "-e", program],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def wcag_contrast(first: str, second: str) -> float:
    """The WCAG 2 contrast ratio of two #rrggbb colours, computed here."""

    def luminance(colour: str) -> float:
        linear: list[float] = []
        for offset in (1, 3, 5):
            value = int(colour[offset : offset + 2], 16) / 255
            linear.append(
                value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
            )
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


# The accent and the text on it, as accentColors returns them.
PAINTED: TypeAdapter[dict[str, str]] = TypeAdapter(dict[str, str])
PAINTED_LIST: TypeAdapter[list[dict[str, str]]] = TypeAdapter(list[dict[str, str]])
# Every #rgb colour: 4096 accents from black to white through every hue.
EVERY_SHORT_HEX: list[str] = [
    f"#{red:x}{green:x}{blue:x}"
    for red in range(16)
    for green in range(16)
    for blue in range(16)
]


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
class TestWidgetColours:
    @pytest.mark.parametrize(
        ("accent", "painted", "text_colour"),
        [
            # The widget's own clay and dark brand colours keep white text.
            ("#ad5732", "#ad5732", "#ffffff"),
            ("#1d4ed8", "#1d4ed8", "#ffffff"),
            ("#000", "#000000", "#ffffff"),
            # Light colours keep the owner's colour with ink text.
            ("#f59e0b", "#f59e0b", "#1a1816"),
            ("#fde047", "#fde047", "#1a1816"),
            ("#ffffff", "#ffffff", "#1a1816"),
        ],
    )
    def test_text_on_the_accent_is_white_else_ink(
        self, accent: str, painted: str, text_colour: str
    ) -> None:
        assert PAINTED.validate_json(
            run_colour_script(f'accentColors("{accent}")')
        ) == {
            "accent": painted,
            "onAccent": text_colour,
        }

    def test_a_mid_tone_neither_text_reads_on_is_darkened_until_white_does(
        self,
    ) -> None:
        colours = PAINTED.validate_json(run_colour_script('accentColors("#808080")'))

        assert colours["onAccent"] == "#ffffff"
        assert colours["accent"] != "#808080"
        assert wcag_contrast(colours["accent"], "#ffffff") >= 4.5

    def test_any_business_colour_keeps_wcag_aa_on_header_launcher_and_send(
        self,
    ) -> None:
        painted = PAINTED_LIST.validate_json(
            run_colour_script(f"{json.dumps(EVERY_SHORT_HEX)}.map(accentColors)")
        )

        failing = [
            (accent, colours)
            for accent, colours in zip(EVERY_SHORT_HEX, painted, strict=True)
            if wcag_contrast(colours["accent"], colours["onAccent"]) < 4.5
        ]
        assert failing == []

    @pytest.mark.parametrize(
        ("attribute", "theme"),
        [("dark", "dark"), (" Light ", "light"), ("sepia", ""), ("", "")],
    )
    def test_the_script_tag_may_ask_for_a_theme(
        self, attribute: str, theme: str
    ) -> None:
        assert json.loads(run_colour_script(f'chooseTheme("{attribute}")')) == theme


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
