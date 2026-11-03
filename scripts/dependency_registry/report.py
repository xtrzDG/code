"""
The report of the registry check of new dependencies
(scripts/dependency_registry_review.py): one row per new direct
dependency with what its registry measured, then every signal, accepted
ones marked with their reason; and the GitHub annotations of the run.
"""

import datetime

from scripts.dependency_registry.manifests import Dependency
from scripts.dependency_registry.registry_facts import PackageFacts
from scripts.dependency_registry.risk_signals import FAIL, Signal

NOT_MEASURED: str = "not published"


def day(value: datetime.datetime | None) -> str:
    return value.date().isoformat() if value is not None else NOT_MEASURED


def yes_no(value: bool | None) -> str:
    if value is None:
        return NOT_MEASURED
    return "yes" if value else "no"


def cell(value: str | None) -> str:
    return (value or NOT_MEASURED).replace("|", "\\|")


def row(dependency: Dependency, facts: PackageFacts) -> str:
    if not facts.exists:
        empty = " |" * 6
        where = f"| {dependency.key} | `{dependency.manifest}`"
        return f"{where} | not on the registry |{empty}"
    publishers = NOT_MEASURED if facts.publishers is None else str(facts.publishers)
    return (
        f"| {dependency.key} | `{dependency.manifest}` | {day(facts.first_release)}"
        f" | {day(facts.latest_release)} | {publishers}"
        f" | {yes_no(facts.runs_code_on_install)} | {yes_no(facts.closed)}"
        f" | {cell(facts.licence)} | {cell(facts.repository)} |"
    )


def render(
    measured: list[tuple[Dependency, PackageFacts, list[Signal]]],
    accepted: dict[str, tuple[frozenset[str], str]],
) -> str:
    lines = ["## New dependencies on their registries", ""]
    if not measured:
        lines.append("This pull request adds no direct dependency.")
        return "\n".join(lines) + "\n"
    lines += [
        "| Package | Manifest | First release | Latest release | Publishers"
        " | Code on install | Deprecated or archived | Licence | Source |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        *(row(dependency, facts) for dependency, facts, _ in measured),
        "",
    ]
    for dependency, _, found in measured:
        codes, reason = accepted.get(dependency.key, (frozenset[str](), ""))
        for signal in found:
            note = f" (accepted: {reason})" if signal.code in codes else ""
            mark = "**fails**" if signal.level == FAIL and not note else signal.level
            lines.append(
                f"- {dependency.key}: {signal.code}, {signal.text}: {mark}{note}"
            )
    return "\n".join(lines) + "\n"


def annotations(
    measured: list[tuple[Dependency, PackageFacts, list[Signal]]],
    accepted: dict[str, tuple[frozenset[str], str]],
) -> list[str]:
    """`::error::` for a failing signal nobody accepted, `::warning::` for the rest."""

    lines: list[str] = []
    for dependency, _, found in measured:
        codes = accepted.get(dependency.key, (frozenset[str](), ""))[0]
        for signal in found:
            failing = signal.level == FAIL and signal.code not in codes
            command = "error" if failing else "warning"
            lines.append(
                f"::{command} file={dependency.manifest},title=New dependency"
                f" {dependency.key}::{signal.code}: {signal.text}"
            )
    return lines
