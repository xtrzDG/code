"""
A failed screenshot's differences are told in the job log.

scripts/screenshot_diff_regions.py reads the `-diff.png` pictures Playwright
writes for the visual tests and prints where their changed (pure red)
pixels lie, so a CI failure says which part of the page moved without the
report artifact being downloaded.
"""

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from scripts.screenshot_diff_regions import (
    EXIT_MISSING,
    EXIT_OK,
    Region,
    changed_regions,
    describe_diff,
    main,
)

RED: tuple[int, int, int] = (255, 0, 0)
FADED: tuple[int, int, int] = (200, 200, 200)


def diff_with(
    size: tuple[int, int], boxes: list[tuple[int, int, int, int]]
) -> Image.Image:
    """A faded picture with these inclusive boxes painted as changed pixels."""
    picture = Image.new("RGB", size, FADED)
    draw = ImageDraw.Draw(picture)
    for box in boxes:
        draw.rectangle(box, fill=RED)
    return picture


def test_changed_pixels_close_together_form_one_region_the_largest_first() -> None:
    diff = diff_with((120, 60), [(70, 40, 72, 41), (10, 10, 19, 19), (21, 20, 22, 21)])

    regions = changed_regions(diff)

    # The two boxes in neighbouring cells are one region; the far one is another.
    assert regions == [
        Region(left=10, top=10, right=22, bottom=21, changed=104),
        Region(left=70, top=40, right=72, bottom=41, changed=6),
    ]


def test_red_that_is_not_pure_is_not_counted() -> None:
    diff = Image.new("RGB", (20, 20), FADED)
    diff.putpixel((5, 5), (254, 0, 0))
    diff.putpixel((6, 6), (255, 1, 1))

    assert changed_regions(diff) == []


def test_a_small_region_is_drawn_from_the_baseline_and_from_the_run(
    tmp_path: Path,
) -> None:
    diff_with((60, 40), [(20, 10, 27, 17)]).save(
        tmp_path / "badge-1440-dark-en-diff.png"
    )
    baseline = Image.new("RGB", (60, 40), (255, 255, 255))
    ImageDraw.Draw(baseline).rectangle((20, 10, 27, 17), fill=(0, 0, 0))
    baseline.save(tmp_path / "badge-1440-dark-en-expected.png")
    Image.new("RGB", (60, 40), (255, 255, 255)).save(
        tmp_path / "badge-1440-dark-en-actual.png"
    )

    lines = describe_diff(tmp_path / "badge-1440-dark-en-diff.png")

    assert lines[0] == "badge-1440-dark-en: 64 px changed in 1 region(s)"
    assert lines[1] == "  x 20-27, y 10-17 (8x8), 64 px changed"
    baseline_at = lines.index("  the largest region, baseline:")
    run_at = lines.index("  the largest region, this run:")
    # The margin around the 8x8 box: 16 rows of 16 characters each.
    baseline_rows = lines[baseline_at + 1 : run_at]
    run_rows = lines[run_at + 1 :]
    assert len(baseline_rows) == len(run_rows) == 16
    assert all(len(row) == 4 + 2 + 16 for row in baseline_rows + run_rows)
    assert any("@" in row for row in baseline_rows)
    assert not any("@" in row for row in run_rows)


def test_a_large_region_is_only_boxed(tmp_path: Path) -> None:
    diff_with((400, 200), [(10, 10, 309, 109)]).save(tmp_path / "page-diff.png")
    Image.new("RGB", (400, 200), (0, 0, 0)).save(tmp_path / "page-expected.png")

    lines = describe_diff(tmp_path / "page-diff.png")

    assert lines == [
        "page: 30000 px changed in 1 region(s)",
        "  x 10-309, y 10-109 (300x100), 30000 px changed",
    ]


def test_the_command_describes_every_diff_under_the_folder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nested = tmp_path / "matrix-at-1440-px" / "results"
    nested.mkdir(parents=True)
    diff_with((300, 100), [(0, 0, 99, 99)]).save(nested / "main-overview-diff.png")
    (tmp_path / "trace.zip").write_bytes(b"")

    assert main([str(tmp_path)]) == EXIT_OK
    assert capsys.readouterr().out.splitlines() == [
        "main-overview: 10000 px changed in 1 region(s)",
        "  x 0-99, y 0-99 (100x100), 10000 px changed",
    ]


def test_a_missing_folder_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([str(tmp_path / "absent")]) == EXIT_MISSING
    assert "is not a folder" in capsys.readouterr().err
