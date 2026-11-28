"""
Where the visual tests' failed screenshots differ, readable in the job log
itself (the visual-report artifact has to be downloaded first, and the page
snapshot of a failed test shows its last page, not the one that differed):

    uv run python -m scripts.screenshot_diff_regions web/e2e/.artifacts/results

For each `<name>-diff.png` Playwright wrote next to `<name>-expected.png`
and `<name>-actual.png`, the regions of its changed pixels (Playwright paints
them pure red) as boxes in CSS pixels, the largest first, each with how
many changed pixels it holds. A small region is drawn in text too, from the
baseline and from the run, so a missing badge or a moved line can be read
without the pictures. .github/scripts/show-e2e-failures.sh runs it after a
failed run. Exit codes: 0 with the descriptions (none for a folder without
diffs), 2 when the folder is missing.
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

EXIT_OK: int = 0
EXIT_MISSING: int = 2
DESCRIPTION: str = "Describes where the visual tests' failed screenshots differ."
DIFF_SUFFIX: str = "-diff.png"
# Changed pixels in Playwright's diff image; the rest is a faded grey copy.
CHANGED_RGB: tuple[int, int, int] = (255, 0, 0)
# Changed pixels this close together belong to one region.
CELL_PX: int = 8
REGIONS_SHOWN: int = 8
# A region at most this large is drawn in text, one character per pixel.
DRAWN_MAX_WIDTH: int = 120
DRAWN_MAX_HEIGHT: int = 40
DRAWN_MARGIN_PX: int = 4
# Darkest to lightest.
SHADES: str = "@%#*+=-:. "


@dataclass(frozen=True)
class Region:
    """A box of changed pixels: inclusive pixel bounds and the changed count."""

    left: int
    top: int
    right: int
    bottom: int
    changed: int

    def describe(self) -> str:
        return (
            f"x {self.left}-{self.right}, y {self.top}-{self.bottom}"
            f" ({self.right - self.left + 1}x{self.bottom - self.top + 1}),"
            f" {self.changed} px changed"
        )


def changed_regions(diff: Image.Image) -> list[Region]:
    """The diff's changed pixels grouped into regions, the largest first."""
    rgb = diff.convert("RGB")
    width, height = rgb.size
    data = rgb.tobytes()
    cells: dict[tuple[int, int], list[int]] = {}
    for y in range(height):
        row = y * width * 3
        for x in range(width):
            index = row + x * 3
            if (data[index], data[index + 1], data[index + 2]) != CHANGED_RGB:
                continue
            cell = cells.setdefault((x // CELL_PX, y // CELL_PX), [x, y, x, y, 0])
            cell[0] = min(cell[0], x)
            cell[1] = min(cell[1], y)
            cell[2] = max(cell[2], x)
            cell[3] = max(cell[3], y)
            cell[4] += 1
    regions: list[Region] = []
    seen: set[tuple[int, int]] = set()
    for start in sorted(cells):
        if start in seen:
            continue
        seen.add(start)
        group = [start]
        pending = [start]
        while pending:
            column, line = pending.pop()
            for near_column in (column - 1, column, column + 1):
                for near_line in (line - 1, line, line + 1):
                    near = (near_column, near_line)
                    if near in cells and near not in seen:
                        seen.add(near)
                        group.append(near)
                        pending.append(near)
        boxes = [cells[key] for key in group]
        regions.append(
            Region(
                left=min(box[0] for box in boxes),
                top=min(box[1] for box in boxes),
                right=max(box[2] for box in boxes),
                bottom=max(box[3] for box in boxes),
                changed=sum(box[4] for box in boxes),
            )
        )
    return sorted(
        regions, key=lambda region: (-region.changed, region.top, region.left)
    )


def drawn(picture: Image.Image, region: Region) -> list[str]:
    """The region (with a small margin) in text, one character per pixel."""
    grey = picture.convert("L")
    width, height = grey.size
    left = max(0, region.left - DRAWN_MARGIN_PX)
    top = max(0, region.top - DRAWN_MARGIN_PX)
    right = min(width - 1, region.right + DRAWN_MARGIN_PX)
    bottom = min(height - 1, region.bottom + DRAWN_MARGIN_PX)
    data = grey.tobytes()
    last = len(SHADES) - 1
    return [
        "".join(
            SHADES[data[y * width + x] * last // 255] for x in range(left, right + 1)
        )
        for y in range(top, bottom + 1)
    ]


def is_drawable(region: Region) -> bool:
    return (
        region.right - region.left + 1 + 2 * DRAWN_MARGIN_PX <= DRAWN_MAX_WIDTH
        and region.bottom - region.top + 1 + 2 * DRAWN_MARGIN_PX <= DRAWN_MAX_HEIGHT
    )


def describe_diff(diff_path: Path) -> list[str]:
    """The lines that tell where one failed screenshot differs."""
    name = diff_path.name.removesuffix(DIFF_SUFFIX)
    with Image.open(diff_path) as diff:
        regions = changed_regions(diff)
    total = sum(region.changed for region in regions)
    lines = [f"{name}: {total} px changed in {len(regions)} region(s)"]
    for region in regions[:REGIONS_SHOWN]:
        lines.append(f"  {region.describe()}")
    if len(regions) > REGIONS_SHOWN:
        lines.append(f"  ... and {len(regions) - REGIONS_SHOWN} smaller region(s)")
    largest = regions[0] if regions else None
    if largest is None or not is_drawable(largest):
        return lines
    for label, suffix in (("baseline", "-expected.png"), ("this run", "-actual.png")):
        picture_path = diff_path.with_name(f"{name}{suffix}")
        if not picture_path.is_file():
            continue
        with Image.open(picture_path) as picture:
            lines.append(f"  the largest region, {label}:")
            lines.extend(f"    |{row}|" for row in drawn(picture, largest))
    return lines


def describe_results(results: Path) -> list[str]:
    """Every failed screenshot under the results folder, described."""
    lines: list[str] = []
    for diff_path in sorted(results.rglob(f"*{DIFF_SUFFIX}")):
        lines.extend(describe_diff(diff_path))
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("results", type=Path, help="Playwright's results folder.")
    arguments = parser.parse_args(argv)
    results: Path = arguments.results
    if not results.is_dir():
        print(f"{results} is not a folder.", file=sys.stderr)
        return EXIT_MISSING
    for line in describe_results(results):
        print(line)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
