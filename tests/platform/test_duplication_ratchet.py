"""The copy-paste ratchet: jscpd's threshold and the list of large clones."""

import json
import re
from pathlib import Path
from typing import Any

import pytest

from scripts.check_duplication import (
    DEFAULT_CONFIG,
    DEFAULT_LARGE_CLONES,
    DEFAULT_REPORT,
    EXIT_OK,
    EXIT_RATCHET,
    EXIT_UNUSABLE,
    LARGE_CLONE_LINES,
    ClonePair,
    large_clones,
    main,
    threshold_notice,
)

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
JSCPD_VERSION_PATTERN: re.Pattern[str] = re.compile(r"jscpd@(\d+\.\d+\.\d+)")
CI_VERSION_PATTERN: re.Pattern[str] = re.compile(r'JSCPD_VERSION: "(\d+\.\d+\.\d+)"')


def clone(first: str, second: str, lines: int) -> dict[str, Any]:
    return {
        "lines": lines,
        "firstFile": {"name": first, "start": 10},
        "secondFile": {"name": second, "start": 40},
    }


def report(*duplicates: dict[str, Any], percentage: float = 1.0) -> dict[str, Any]:
    return {
        "duplicates": list(duplicates),
        "statistics": {"total": {"percentage": percentage}},
    }


def write(path: Path, document: object) -> Path:
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def run_check(
    tmp_path: Path,
    current: dict[str, Any],
    allowed: list[dict[str, Any]],
    *extra: str,
) -> int:
    return main(
        [
            "--report",
            str(write(tmp_path / "report.json", current)),
            "--allowed",
            str(write(tmp_path / "allowed.json", {"clones": allowed})),
            "--config",
            str(write(tmp_path / "config.json", {"threshold": 1.0})),
            *extra,
        ]
    )


def test_only_clones_over_twenty_lines_are_large() -> None:
    found = large_clones(
        report(
            clone("app/b.py", "app/a.py", LARGE_CLONE_LINES),
            clone("app/b.py", "app/a.py", LARGE_CLONE_LINES + 1),
        )
    )

    assert [(item.pair, item.lines) for item in found] == [
        (ClonePair("app/a.py", "app/b.py"), LARGE_CLONE_LINES + 1)
    ]
    assert found[0].locations == "app/b.py:10 and app/a.py:40"


def test_a_listed_clone_passes_whichever_file_jscpd_names_first(
    tmp_path: Path,
) -> None:
    current = report(clone("app/b.py", "app/a.py", 30))

    assert (
        run_check(tmp_path, current, [{"files": ["app/a.py", "app/b.py"], "count": 1}])
        == EXIT_OK
    )


def test_a_new_large_clone_fails_and_names_both_places(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    current = report(
        clone("app/a.py", "app/b.py", 30), clone("web/x.ts", "web/y.ts", 22)
    )

    exit_code = run_check(
        tmp_path, current, [{"files": ["app/a.py", "app/b.py"], "count": 1}]
    )

    assert exit_code == EXIT_RATCHET
    error = capsys.readouterr().err
    assert "22 lines: web/x.ts:10 and web/y.ts:40" in error
    assert "app/a.py" not in error


def test_a_second_clone_of_a_listed_pair_is_new(tmp_path: Path) -> None:
    current = report(
        clone("app/a.py", "app/b.py", 30), clone("app/a.py", "app/b.py", 25)
    )

    assert (
        run_check(tmp_path, current, [{"files": ["app/a.py", "app/b.py"], "count": 1}])
        == EXIT_RATCHET
    )


def test_a_listed_clone_that_is_gone_must_leave_the_list(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = run_check(
        tmp_path, report(), [{"files": ["app/a.py", "app/b.py"], "count": 1}]
    )

    assert exit_code == EXIT_RATCHET
    assert "--update" in capsys.readouterr().err


def test_update_writes_the_list_the_check_then_accepts(tmp_path: Path) -> None:
    current = report(
        clone("app/b.py", "app/a.py", 30),
        clone("app/a.py", "app/b.py", 21),
        clone("web/x.ts", "web/y.ts", 9),
    )
    report_path = write(tmp_path / "report.json", current)
    allowed_path = tmp_path / "allowed.json"
    config_path = write(tmp_path / "config.json", {"threshold": 1.0})
    arguments = ["--report", str(report_path), "--allowed", str(allowed_path)]

    assert main([*arguments, "--update"]) == EXIT_OK
    assert json.loads(allowed_path.read_text(encoding="utf-8")) == {
        "clones": [{"files": ["app/a.py", "app/b.py"], "count": 2}]
    }
    assert main([*arguments, "--config", str(config_path)]) == EXIT_OK


@pytest.mark.parametrize("content", ["{not json", "[]", '{"duplicates": 3}'])
def test_an_unusable_report_is_reported(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    content: str,
) -> None:
    (tmp_path / "report.json").write_text(content, encoding="utf-8")

    exit_code = main(
        ["--report", str(tmp_path / "report.json"), "--allowed", "missing.json"]
    )

    assert exit_code == EXIT_UNUSABLE
    assert "Cannot check the duplication" in capsys.readouterr().err


def test_a_share_well_below_the_threshold_asks_to_lower_it() -> None:
    assert threshold_notice(report(percentage=1.3), {"threshold": 1.34}) is None
    notice = threshold_notice(report(percentage=1.2412), {"threshold": 1.36})
    assert notice is not None
    assert 'lower "threshold" in .jscpd.json to 1.25' in notice


def test_the_committed_config_ignores_containers_and_generated_files() -> None:
    config = json.loads((PROJECT_ROOT / DEFAULT_CONFIG).read_text(encoding="utf-8"))

    assert config["minLines"] == 8
    assert {"app/containers/**", "web/src/api/schema.d.ts"} <= set(config["ignore"])
    assert "web/src/**/*.generated.ts" in config["ignore"]
    assert 0 < float(config["threshold"]) < 2
    assert "json" in config["reporters"]
    assert Path(config["output"]) == DEFAULT_REPORT.parent


def test_the_committed_list_is_sorted_and_names_files_that_exist() -> None:
    document = json.loads(
        (PROJECT_ROOT / DEFAULT_LARGE_CLONES).read_text(encoding="utf-8")
    )
    pairs = [tuple(entry["files"]) for entry in document["clones"]]

    assert pairs == sorted(pairs)
    assert all(pair == tuple(sorted(pair)) for pair in pairs)
    assert all(entry["count"] >= 1 for entry in document["clones"])
    missing = [
        name for pair in pairs for name in pair if not (PROJECT_ROOT / name).is_file()
    ]
    assert missing == [], "Run `just duplication` and the check with --update."


def test_ci_and_the_justfile_run_the_same_jscpd() -> None:
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    justfile = (PROJECT_ROOT / "justfile").read_text(encoding="utf-8")
    ci_versions = CI_VERSION_PATTERN.findall(workflow)

    assert len(ci_versions) == 1
    assert JSCPD_VERSION_PATTERN.findall(justfile) == ci_versions
    assert "--config .jscpd.json" in workflow
    assert "python -m scripts.check_duplication" in workflow


def test_just_check_runs_the_duplication_ratchet() -> None:
    # `just check` is documented as every check CI runs; CI runs jscpd.
    justfile = (PROJECT_ROOT / "justfile").read_text(encoding="utf-8")
    check_line = next(
        line for line in justfile.splitlines() if line.startswith("check:")
    )

    assert "duplication" in check_line.removeprefix("check:").split()
