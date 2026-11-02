"""
The nightly dependency audit (.github/workflows/dependency-audit.yml): the
JSON reports of pip-audit (uv.lock) and npm audit (web/, integrations/zapier/)
as one list of advisories, each with its remediation deadline, and what to
do with the issue "Dependency advisories":

    uv run --no-project python -m scripts.dependency_advisories \\
        --pip-audit uv.lock="$RUNNER_TEMP/audit/uv.json" \\
        --npm-audit web/package-lock.json="$RUNNER_TEMP/audit/web.json" \\
        --known "$RUNNER_TEMP/known.md" --body "$RUNNER_TEMP/body.md" \\
        --action "$RUNNER_TEMP/action" --summary "$GITHUB_STEP_SUMMARY"

Remediation deadlines count from the day an advisory was first reported:
critical 2 days, high 7, moderate 30, low 90 (the next quarterly review).
pip-audit names no severity: a Python advisory counts as high (CI's
pip-audit gate refuses any). The issue keeps one marker per advisory with
the day it was first seen, so a deadline never moves; `--known` is the open
issue's text (body and comments), left out when none is open.

The action file gets `create` (advisories and no open issue), `comment`
(advisories not reported yet), `close` (none left) or `none`. Exit codes:
0 reported, 1 a critical or high advisory is past its deadline, 2 a report
cannot be read (the audit proves nothing).
"""

import argparse
import datetime
import json
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

EXIT_REPORTED: int = 0
EXIT_OVERDUE: int = 1
EXIT_UNUSABLE: int = 2
# Days to remediate by severity; an unknown severity gets the shortest.
DEADLINE_DAYS: dict[str, int] = {
    "critical": 2,
    "high": 7,
    "moderate": 30,
    "low": 90,
    "info": 90,
}
SHORTEST_DEADLINE_DAYS: int = 2
FAILING: frozenset[str] = frozenset({"critical", "high"})
PYTHON_SEVERITY: str = "high"
MARKER: re.Pattern[str] = re.compile(
    r"<!-- advisory: (?P<key>.+?) \| first-seen (?P<day>\d{4}-\d{2}-\d{2}) -->"
)


class AuditReportError(ValueError):
    """A report that cannot be read: the audit proves nothing."""


@dataclass(frozen=True)
class Advisory:
    lockfile: str
    package: str
    identifier: str
    severity: str
    affected: str
    fix: str

    @property
    def key(self) -> str:
        return f"{self.lockfile} {self.package} {self.identifier}"


def load(path: Path) -> dict[str, Any]:
    try:
        document: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise AuditReportError(f"{path}: unreadable ({error})") from error
    if not isinstance(document, dict):
        raise AuditReportError(f"{path}: not an audit report")
    return cast(dict[str, Any], document)


def python_advisories(lockfile: str, report: dict[str, Any]) -> list[Advisory]:
    if not isinstance(report.get("dependencies"), list):
        raise AuditReportError(f"{lockfile}: not a pip-audit report")
    found: list[Advisory] = []
    for dependency in cast(list[dict[str, Any]], report["dependencies"]):
        for vulnerability in cast(list[dict[str, Any]], dependency.get("vulns", [])):
            fixes = [str(each) for each in vulnerability.get("fix_versions", [])]
            found.append(
                Advisory(
                    lockfile=lockfile,
                    package=str(dependency["name"]),
                    identifier=str(vulnerability["id"]),
                    severity=PYTHON_SEVERITY,
                    affected=str(dependency.get("version", "")),
                    fix=f"upgrade to {fixes[0]}" if fixes else "no fix yet",
                )
            )
    return found


def npm_fix(vulnerability: dict[str, Any]) -> str:
    available: object = vulnerability.get("fixAvailable")
    if available is True:
        return "`npm audit fix`"
    if isinstance(available, dict):
        fix = cast(dict[str, Any], available)
        major = " (a major)" if fix.get("isSemVerMajor") else ""
        return f"{fix.get('name')}@{fix.get('version')}{major}"
    return "no fix yet"


def npm_advisories(lockfile: str, report: dict[str, Any]) -> list[Advisory]:
    vulnerabilities: object = report.get("vulnerabilities")
    if "error" in report or not isinstance(vulnerabilities, dict):
        raise AuditReportError(f"{lockfile}: not an npm audit report")
    found: dict[str, Advisory] = {}
    for entry in cast(dict[str, dict[str, Any]], vulnerabilities).values():
        for via in cast(list[object], entry.get("via", [])):
            if not isinstance(via, dict):
                continue  # Only names the package it comes through.
            source = cast(dict[str, Any], via)
            url = str(source.get("url", ""))
            advisory = Advisory(
                lockfile=lockfile,
                package=str(source.get("name")),
                identifier=url.rstrip("/").rsplit("/", 1)[-1] or str(source["source"]),
                severity=str(source.get("severity", "low")),
                affected=str(source.get("range", "")),
                fix=npm_fix(entry),
            )
            found.setdefault(advisory.key, advisory)
    return list(found.values())


def first_seen(known: str) -> dict[str, datetime.date]:
    return {
        match["key"]: datetime.date.fromisoformat(match["day"])
        for match in MARKER.finditer(known)
    }


def due(advisory: Advisory, seen: datetime.date) -> datetime.date:
    return seen + datetime.timedelta(
        days=DEADLINE_DAYS.get(advisory.severity, SHORTEST_DEADLINE_DAYS)
    )


def cell(text: str) -> str:
    """Text for a Markdown table cell: npm ranges hold `||`, a column break."""

    return " ".join(text.split()).replace("|", "\\|")


def table(
    advisories: Sequence[Advisory], seen: dict[str, datetime.date], today: datetime.date
) -> list[str]:
    rows = sorted(advisories, key=lambda each: (due(each, seen[each.key]), each.key))
    lines = [
        "| Due | Severity | Lockfile | Package | Advisory | Affected | Fix |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for each in rows:
        deadline = due(each, seen[each.key])
        late = " **(overdue)**" if deadline < today else ""
        lines.append(
            f"| {deadline.isoformat()}{late} | {cell(each.severity)}"
            f" | `{cell(each.lockfile)}` | {cell(each.package)}"
            f" | {cell(each.identifier)} | {cell(each.affected)} | {cell(each.fix)} |"
        )
    return lines


def body(
    advisories: Sequence[Advisory],
    new: Sequence[Advisory],
    seen: dict[str, datetime.date],
    today: datetime.date,
) -> str:
    lines = [
        f"## Dependency advisories: {len(advisories)} open, {len(new)} new",
        "",
        "Remediation deadline from the day an advisory was first reported:"
        ' critical 2 days, high 7, moderate 30, low 90 (SECURITY.md, "Triage'
        ' of automated findings"). Fix first: upgrade, or replace the package;'
        " one that cannot be fixed yet gets a comment here with the reason. A"
        " critical or high one past its deadline turns the nightly audit red.",
        "",
        *table(advisories, seen, today),
        "",
        "The nightly audit closes this issue once no advisory is left.",
        "",
        *(
            f"<!-- advisory: {each.key} | first-seen {seen[each.key].isoformat()} -->"
            for each in sorted(advisories, key=lambda each: each.key)
        ),
    ]
    return "\n".join(lines) + "\n"


def action_of(
    issue_open: bool, advisories: Sequence[Advisory], new: Sequence[Advisory]
) -> str:
    if not advisories:
        return "close" if issue_open else "none"
    if not issue_open:
        return "create"
    return "comment" if new else "none"


def pairs(values: Sequence[str]) -> list[tuple[str, Path]]:
    found: list[tuple[str, Path]] = []
    for value in values:
        lockfile, separator, report = value.partition("=")
        if not separator or not lockfile or not report:
            raise AuditReportError(f"{value!r}: expected <lockfile>=<report.json>")
        found.append((lockfile, Path(report)))
    return found


def collect(parsed: argparse.Namespace) -> list[Advisory]:
    advisories: list[Advisory] = []
    for lockfile, path in pairs(parsed.pip_audit):
        advisories += python_advisories(lockfile, load(path))
    for lockfile, path in pairs(parsed.npm_audit):
        advisories += npm_advisories(lockfile, load(path))
    return advisories


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Advisories in the lockfiles.")
    parser.add_argument("--pip-audit", action="append", default=[])
    parser.add_argument("--npm-audit", action="append", default=[])
    parser.add_argument("--known", type=Path, help="the open issue's text")
    parser.add_argument("--today", type=datetime.date.fromisoformat)
    parser.add_argument("--body", type=Path, required=True)
    parser.add_argument("--action", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    parsed = parser.parse_args(arguments)
    today: datetime.date = parsed.today or datetime.datetime.now(datetime.UTC).date()

    try:
        advisories = collect(parsed)
        known = parsed.known.read_text(encoding="utf-8") if parsed.known else ""
    except (AuditReportError, OSError, KeyError) as error:
        print(f"::error::Dependency audit: {error}", file=sys.stderr)
        return EXIT_UNUSABLE

    seen = first_seen(known)
    new = [each for each in advisories if each.key not in seen]
    seen |= {each.key: today for each in new}
    text = body(advisories, new, seen, today)
    parsed.body.write_text(text, encoding="utf-8")
    parsed.action.write_text(
        action_of(parsed.known is not None, advisories, new), encoding="utf-8"
    )
    if parsed.summary is not None:
        with parsed.summary.open("a", encoding="utf-8") as summary:
            summary.write(text)
    overdue = [
        each
        for each in advisories
        if each.severity in FAILING and due(each, seen[each.key]) < today
    ]
    for each in overdue:
        print(f"::error::Past its remediation deadline: {each.key} ({each.severity})")
    return EXIT_OVERDUE if overdue else EXIT_REPORTED


if __name__ == "__main__":
    sys.exit(main())
