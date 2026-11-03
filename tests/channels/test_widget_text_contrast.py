"""
Text the widget shows on the business's accent (the business's name and
the AI disclosure line in the header) keeps its full colour: accentColors
picks that colour for WCAG AA (4.5:1) and no more, so a faded line would
fall below AA wherever the title just meets it. The same holds for the
detail under a failed message on its danger tint and for the label of a
voice message still on its way (only its photo fades). The browser audit
(web/e2e/widget-a11y.spec.ts, axe) checks the rendered widget.
"""

import json
import re

import pytest

from tests.channels.widget_node_runner import (
    extract_function,
    extract_variable,
    run_in_node,
)
from tests.channels.widget_script_source import SCRIPT_SOURCE

COLOUR_FUNCTIONS: tuple[str, ...] = (
    "accentColors",
    "hexChannels",
    "toHexColor",
    "relativeLuminance",
    "contrastRatio",
)
COLOUR_CONSTANTS: tuple[str, ...] = (
    "AA_CONTRAST",
    "WHITE_TEXT",
    "INK_TEXT",
    "DARKEN_STEP",
)


def stylesheet(name: str) -> str:
    """A stylesheet's literal text (its `var <name> = [...]` strings, joined)."""

    match = re.search(rf"var {name} = \[(.*?)\]\.join\(\"\"\);", SCRIPT_SOURCE, re.S)
    assert match is not None
    return "".join(re.findall(r'"((?:[^"\\]|\\.)*)"', match.group(1)))


def widget_css() -> str:
    """The main stylesheet (`var CSS`)."""

    return stylesheet("CSS")


def declarations(css: str, selector: str) -> str:
    """Every declaration of the rules written for exactly `selector`."""

    pattern: str = r"(?:^|[}])" + re.escape(selector) + r"\{([^}]*)\}"
    found: list[str] = re.findall(pattern, css)
    assert found, selector
    return ";".join(found)


@pytest.mark.parametrize(
    "selector",
    [".aw-header", ".aw-heading", ".aw-title", ".aw-subtitle", ".aw-error-detail"],
)
def test_text_on_a_colour_chosen_for_aa_is_never_faded(selector: str) -> None:
    assert "opacity" not in declarations(widget_css(), selector)


def test_an_upload_on_its_way_fades_its_photo_and_mutes_its_label() -> None:
    media: str = stylesheet("MEDIA_CSS")
    busy: str = declarations(media, ".aw-tray-item[aria-busy=true]")

    assert "opacity" not in busy
    assert "color:var(--aw-muted)" in busy
    assert "opacity" in declarations(media, ".aw-tray-item[aria-busy=true] img")


def test_the_header_text_is_the_colour_chosen_for_the_accent() -> None:
    header: str = declarations(widget_css(), ".aw-header")

    assert "background:var(--aw-accent)" in header
    assert "color:var(--aw-on-accent)" in header
    assert "color:" not in declarations(widget_css(), ".aw-subtitle")


# White text just at AA (4.54:1), a grey darkened until white reaches it,
# the default accent, and two that take the ink text (a yellow, a blue).
ACCENTS: tuple[str, ...] = ("#767676", "#777777", "#ad5732", "#ffcc00", "#3b82f6")


@pytest.mark.parametrize("accent", ACCENTS)
def test_the_text_on_any_accent_reaches_aa_at_full_strength(accent: str) -> None:
    program: str = (
        "".join(extract_variable(name) for name in COLOUR_CONSTANTS)
        + "".join(extract_function(name) for name in COLOUR_FUNCTIONS)
        + f"var colors = accentColors({json.dumps(accent)});\n"
        + "console.log(JSON.stringify(contrastRatio(hexChannels(colors.accent),"
        + " hexChannels(colors.onAccent))));"
    )

    ratio = run_in_node(program)

    assert isinstance(ratio, int | float)
    assert ratio >= 4.5
