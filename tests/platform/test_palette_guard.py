"""
The product's colours stay in its palette: warm graphite and paper
neutrals, one clay accent, and muted olive, ochre, brick and slate states
(web/src/app/globals.css). Nothing shipped to a browser (the cabinet's
sources and public files, the widget and its demo page) or seeded as a
demo business's brand colour may use a green, mint, cyan, indigo or purple
hue again, like the retired palettes did (#4f46e5 indigo, #34d399 mint,
#38bdf8 cyan, the sage #4a6739/#a9bf94 "done" tone, the demo chats'
#2F7D4F and #8E5A9B, the teal #0f766e example).

A colour counts when it is saturated enough to read as a hue (HSL
saturation >= 0.22, lightness between 0.12 and 0.93); the families are
the screenshot tour's: green 75-165 deg, cyan 165-200, indigo 235-265,
purple 265-320. Tests are not scanned: their fixtures model colours owners
pick for their own brand.
"""

import colorsys
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
SCANNED_ROOTS: tuple[tuple[str, frozenset[str]], ...] = (
    ("web/src", frozenset({".ts", ".tsx", ".mts", ".css", ".svg", ".json"})),
    (
        "web/public",
        frozenset({".js", ".svg", ".json", ".webmanifest", ".html", ".css"}),
    ),
    ("app/gateways/http/static", frozenset({".js", ".html", ".css"})),
    ("app/registries/demo", frozenset({".py"})),
)
SKIPPED_NAME_PATTERNS: tuple[str, ...] = ("*.test.ts", "*.test.tsx", "*.generated.ts")
# Other companies' marks keep their own hue, softened (the cabinet's outline
# style of the WhatsApp logo); one line per colour, with the reason.
ALLOWED_COLOURS: frozenset[tuple[str, str]] = frozenset(
    {
        ("web/src/lib/channelMarks.ts", "#8cc29b"),  # WhatsApp mark, light end
        ("web/src/lib/channelMarks.ts", "#3f7d57"),  # WhatsApp mark, dark end
    }
)
BANNED_FAMILIES: tuple[tuple[str, float, float], ...] = (
    ("green", 75.0, 165.0),
    ("cyan", 165.0, 200.0),
    ("indigo", 235.0, 265.0),
    ("purple", 265.0, 320.0),
)
# Six or eight hex digits, or three with at least one letter ("#418" is a
# React error number in a comment, not a colour).
HEX_COLOUR: re.Pattern[str] = re.compile(
    r"(?<![\w&])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|(?=[0-9]*[a-fA-F])[0-9a-fA-F]{3})\b"
)
RGB_COLOUR: re.Pattern[str] = re.compile(
    r"rgba?\(\s*(\d{1,3})[\s,]+(\d{1,3})[\s,]+(\d{1,3})"
)


@dataclass(frozen=True)
class OffPaletteColour:
    relative_path: str
    line_number: int
    colour: str
    family: str


def hue_family(red: int, green: int, blue: int) -> str | None:
    hue, lightness, saturation = colorsys.rgb_to_hls(red / 255, green / 255, blue / 255)
    if saturation < 0.22 or lightness < 0.12 or lightness > 0.93:
        return None

    degrees: float = hue * 360
    for name, start, end in BANNED_FAMILIES:
        if start <= degrees < end:
            return name

    return None


def hex_channels(colour: str) -> tuple[int, int, int]:
    digits: str = colour.removeprefix("#")
    if len(digits) == 3:
        digits = "".join(digit * 2 for digit in digits)

    return int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16)


def colours_in_line(line: str) -> list[tuple[str, tuple[int, int, int]]]:
    found: list[tuple[str, tuple[int, int, int]]] = [
        (match.group(0).lower(), hex_channels(match.group(0)))
        for match in HEX_COLOUR.finditer(line)
    ]
    for match in RGB_COLOUR.finditer(line):
        channels = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        if max(channels) <= 255:
            found.append((match.group(0), channels))

    return found


def scanned_files() -> list[Path]:
    files: list[Path] = []
    for root_name, suffixes in SCANNED_ROOTS:
        for path in sorted((PROJECT_ROOT / root_name).rglob("*")):
            if not path.is_file() or path.suffix not in suffixes:
                continue

            if any(
                PurePosixPath(path.name).match(pattern)
                for pattern in SKIPPED_NAME_PATTERNS
            ):
                continue

            files.append(path)

    return files


def find_off_palette_colours() -> list[OffPaletteColour]:
    found: list[OffPaletteColour] = []
    for path in scanned_files():
        relative_path: str = path.relative_to(PROJECT_ROOT).as_posix()
        text: str = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for colour, channels in colours_in_line(line):
                family: str | None = hue_family(*channels)
                if family is None or (relative_path, colour) in ALLOWED_COLOURS:
                    continue

                found.append(
                    OffPaletteColour(relative_path, line_number, colour, family)
                )

    return found


def test_shipped_colours_stay_in_the_warm_palette() -> None:
    off_palette: list[OffPaletteColour] = find_off_palette_colours()

    assert off_palette == [], (
        "Colours outside the palette (warm neutrals, one clay accent, muted "
        "olive/ochre/brick/slate states). Use the tokens of "
        "web/src/app/globals.css instead:\n"
        + "\n".join(
            f"  {item.relative_path}:{item.line_number} {item.colour} ({item.family})"
            for item in off_palette
        )
    )


def test_the_guard_catches_every_retired_colour() -> None:
    retired: dict[str, str] = {
        "#4f46e5": "indigo",
        "#6366f1": "indigo",
        "#34d399": "green",
        "#38bdf8": "cyan",
        "#4a6739": "green",
        "#a9bf94": "green",
        "#edf1e7": "green",
        "#2F7D4F": "green",
        "#8E5A9B": "purple",
        "#0f766e": "cyan",
        "#13805a": "green",
        "#5b5bd6": "indigo",
    }
    for colour, family in retired.items():
        assert hue_family(*hex_channels(colour)) == family, colour

    assert hue_family(169, 191, 148) == "green"


def test_the_palette_itself_passes() -> None:
    palette: list[str] = [
        "#ad5732",  # clay accent
        "#e19a75",  # clay accent, dark scheme
        "#5c5a2e",  # olive "done"
        "#c2bd8c",  # khaki "done", dark scheme
        "#f0efe2",  # olive soft
        "#86570f",  # ochre warning
        "#b0362b",  # brick danger
        "#3d5c79",  # slate info
        "#98b0c8",  # slate info, dark scheme
        "#141311",  # graphite canvas
        "#f6f5f2",  # paper canvas
    ]
    for colour in palette:
        assert hue_family(*hex_channels(colour)) is None, colour


def test_colours_are_read_in_every_notation() -> None:
    line: str = (
        'a { color: #abc; fill: rgb(169 191 148 / 0.12); b: #12345678; c: "#418" }'
    )

    assert [colour for colour, _ in colours_in_line(line)] == [
        "#abc",
        "#12345678",
        "rgb(169 191 148",
    ]
