"""
The nightly dependency audit (scripts/dependency_advisories.py, run by
.github/workflows/dependency-audit.yml): pip-audit's and npm audit's reports
become one list with remediation deadlines; a new advisory opens or
comments on the issue, none left closes it; a deadline counts from the day
an advisory was first reported, and a critical or high one past it fails.
"""

import datetime
import json
from pathlib import Path
from typing import Any

import pytest

from scripts.dependency_advisories import (
    EXIT_OVERDUE,
    EXIT_REPORTED,
    EXIT_UNUSABLE,
    main,
)

TODAY: datetime.date = datetime.date(2026, 11, 2)
PIP_CLEAN: dict[str, Any] = {
    "dependencies": [{"name": "fastapi", "version": "0.142.2", "vulns": []}],
    "fixes": [],
}
PIP_FINDING: dict[str, Any] = {
    "dependencies": [
        {
            "name": "jinja2",
            "version": "3.1.2",
            "vulns": [
                {"id": "GHSA-h5c8-rqwp-cp95", "fix_versions": ["3.1.3"], "aliases": []}
            ],
        }
    ],
    "fixes": [],
}
UNDICI: dict[str, Any] = {
    "name": "undici",
    "severity": "high",
    "via": [
        {
            "source": 1112496,
            "name": "undici",
            "title": "Denial of service",
            "url": "https://github.com/advisories/GHSA-4qv8-2p9j-2685",
            "severity": "high",
            "range": ">=7.0.0 <7.30.1",
        }
    ],
    "fixAvailable": True,
}
JSDOM: dict[str, Any] = {
    "name": "jsdom",
    "severity": "high",
    "via": ["undici"],
    "fixAvailable": {"name": "jsdom", "version": "30.1.3", "isSemVerMajor": True},
}
NPM_FINDING: dict[str, Any] = {
    "auditReportVersion": 2,
    "vulnerabilities": {"undici": UNDICI, "jsdom": JSDOM},
}
NPM_CLEAN: dict[str, Any] = {"auditReportVersion": 2, "vulnerabilities": {}}
UNDICI_KEY: str = "web/package-lock.json undici GHSA-4qv8-2p9j-2685"


def audit(
    tmp_path: Path,
    pip: object = PIP_CLEAN,
    npm: object = NPM_CLEAN,
    known: str | None = None,
    today: datetime.date = TODAY,
) -> tuple[int, str, str]:
    (tmp_path / "uv.json").write_text(json.dumps(pip), encoding="utf-8")
    (tmp_path / "web.json").write_text(json.dumps(npm), encoding="utf-8")
    arguments = [
        "--pip-audit",
        f"uv.lock={tmp_path / 'uv.json'}",
        "--npm-audit",
        f"web/package-lock.json={tmp_path / 'web.json'}",
        "--body",
        str(tmp_path / "body.md"),
        "--action",
        str(tmp_path / "action"),
        "--today",
        today.isoformat(),
    ]
    if known is not None:
        (tmp_path / "known.md").write_text(known, encoding="utf-8")
        arguments += ["--known", str(tmp_path / "known.md")]
    code = main(arguments)
    action = (tmp_path / "action").read_text(encoding="utf-8")
    body = (tmp_path / "body.md").read_text(encoding="utf-8")
    return code, action, body


def test_no_advisory_and_no_issue_does_nothing(tmp_path: Path) -> None:
    assert audit(tmp_path)[:2] == (EXIT_REPORTED, "none")


def test_a_new_advisory_opens_the_issue_with_its_deadline(tmp_path: Path) -> None:
    code, action, body = audit(tmp_path, PIP_FINDING, NPM_FINDING)

    assert (code, action) == (EXIT_REPORTED, "create")
    assert "2 open, 2 new" in body
    # A Python advisory has no severity: it counts as high (7 days).
    assert "| 2026-11-09 | high | `uv.lock` | jinja2 | GHSA-h5c8-rqwp-cp95" in body
    assert "| upgrade to 3.1.3 |" in body
    assert f"<!-- advisory: {UNDICI_KEY} | first-seen 2026-11-02 -->" in body
    # The package it comes through (jsdom) is not an advisory of its own.
    assert body.count("<!-- advisory:") == 2
    assert "critical 2 days, high 7, moderate 30, low 90" in body


def test_an_open_issue_gets_a_comment_only_for_new_advisories(tmp_path: Path) -> None:
    _, _, first = audit(tmp_path, npm=NPM_FINDING)
    code, action, _ = audit(tmp_path, npm=NPM_FINDING, known=first)

    assert (code, action) == (EXIT_REPORTED, "none")
    code, action, body = audit(tmp_path, PIP_FINDING, NPM_FINDING, known=first)
    assert (code, action) == (EXIT_REPORTED, "comment")
    assert "2 open, 1 new" in body


def test_the_deadline_counts_from_the_first_report(tmp_path: Path) -> None:
    _, _, first = audit(tmp_path, npm=NPM_FINDING)
    later = TODAY + datetime.timedelta(days=8)
    code, action, body = audit(tmp_path, npm=NPM_FINDING, known=first, today=later)

    assert (code, action) == (EXIT_OVERDUE, "none")
    assert "| 2026-11-09 **(overdue)** | high |" in body
    assert f"first-seen {TODAY.isoformat()}" in body


def test_a_late_moderate_advisory_is_listed_but_does_not_fail(tmp_path: Path) -> None:
    moderate = {**UNDICI, "via": [{**UNDICI["via"][0], "severity": "moderate"}]}
    report = {**NPM_FINDING, "vulnerabilities": {"undici": moderate}}
    _, _, first = audit(tmp_path, npm=report)
    code, _, body = audit(
        tmp_path, npm=report, known=first, today=TODAY + datetime.timedelta(days=31)
    )

    assert code == EXIT_REPORTED
    assert "| 2026-12-02 **(overdue)** | moderate |" in body


def test_no_advisory_left_closes_the_open_issue(tmp_path: Path) -> None:
    _, _, first = audit(tmp_path, npm=NPM_FINDING)

    assert audit(tmp_path, known=first)[:2] == (EXIT_REPORTED, "close")


def test_the_fix_names_a_major_upgrade(tmp_path: Path) -> None:
    jsdom_only = {
        **JSDOM,
        "via": [{**UNDICI["via"][0], "name": "jsdom", "url": "https://x/GHSA-1"}],
    }
    report = {**NPM_FINDING, "vulnerabilities": {"jsdom": jsdom_only}}
    _, _, body = audit(tmp_path, npm=report)

    assert "| jsdom@30.1.3 (a major) |" in body


def test_a_range_with_alternatives_stays_in_its_cell(tmp_path: Path) -> None:
    # npm writes "<2.0.1 || >=3.0.0 <3.0.2": unescaped, `|` starts a column.
    split = {**UNDICI, "via": [{**UNDICI["via"][0], "range": "<7.0.1 || >=7.1.0"}]}
    report = {**NPM_FINDING, "vulnerabilities": {"undici": split}}
    _, _, body = audit(tmp_path, npm=report)
    [row] = [line for line in body.splitlines() if line.startswith("| 2026-11-09")]

    assert "| <7.0.1 \\|\\| >=7.1.0 |" in row
    assert row.replace("\\|", "").count("|") == 8


@pytest.mark.parametrize(
    ("pip", "npm"),
    [
        ({"error": "no lockfile"}, NPM_CLEAN),
        (PIP_CLEAN, {"error": {"code": "ENOLOCK", "summary": "no lockfile"}}),
        (PIP_CLEAN, ["not", "a", "report"]),
    ],
)
def test_an_unreadable_report_proves_nothing(
    tmp_path: Path, pip: object, npm: object
) -> None:
    (tmp_path / "uv.json").write_text(json.dumps(pip), encoding="utf-8")
    (tmp_path / "web.json").write_text(json.dumps(npm), encoding="utf-8")
    code = main(
        [
            "--pip-audit",
            f"uv.lock={tmp_path / 'uv.json'}",
            "--npm-audit",
            f"web/package-lock.json={tmp_path / 'web.json'}",
            "--body",
            str(tmp_path / "body.md"),
            "--action",
            str(tmp_path / "action"),
        ]
    )

    assert code == EXIT_UNUSABLE
    assert not (tmp_path / "action").exists()


def test_a_report_argument_names_its_lockfile(tmp_path: Path) -> None:
    code = main(
        [
            "--npm-audit",
            str(tmp_path / "web.json"),
            "--body",
            str(tmp_path / "body.md"),
            "--action",
            str(tmp_path / "action"),
        ]
    )

    assert code == EXIT_UNUSABLE
