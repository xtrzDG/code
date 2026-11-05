"""
The direct dependencies a pull request adds, measured on their registries
(SDLC-02), in the CI job "security" next to GitHub's dependency review:

    git worktree add --detach "$RUNNER_TEMP/base" "$BASE_SHA"
    uv run --no-project python -m scripts.dependency_registry_review \\
        --base "$RUNNER_TEMP/base" --summary "$GITHUB_STEP_SUMMARY"

A dependency is new when no manifest of its ecosystem declared it at the
pull request's base (scripts/dependency_registry/manifests.py). For each,
npm's or PyPI's own data: first and latest release, how many accounts may
publish it, deprecation or archival, code run on install, licence and
source (registry_facts.py); then the signals (risk_signals.py). A failing
signal (not on the registry, deprecated or archived, younger than 30 days,
a lookalike of a popular or already used name, installed from elsewhere
than the registry) fails the step unless
.github/dependency-registry-review.toml accepts it with a reason; warnings
go to the report for the reviewer. The report is the run summary.

Exit codes: 0 nothing new or nothing failing, 1 a failing signal nobody
accepted, 2 a manifest, the exceptions file or a registry could not be
read (nothing was measured).
"""

import argparse
import datetime
import sys
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

from scripts.dependency_registry.manifests import (
    NPM,
    PYPI,
    REGISTRY,
    Dependency,
    ManifestError,
    added,
    declared,
)
from scripts.dependency_registry.popular_names import POPULAR_NPM, POPULAR_PYPI
from scripts.dependency_registry.registry_facts import (
    Fetch,
    PackageFacts,
    RegistryUnavailable,
    https_fetch,
    measure,
)
from scripts.dependency_registry.report import annotations, render
from scripts.dependency_registry.risk_signals import FAIL, Signal, signals

EXIT_PASSED: int = 0
EXIT_FAILED: int = 1
EXIT_UNUSABLE: int = 2
REVIEWED_FILE: str = ".github/dependency-registry-review.toml"

type Accepted = dict[str, tuple[frozenset[str], str]]
type Measured = list[tuple[Dependency, PackageFacts, list[Signal]]]


def reviewed_exceptions(text: str) -> Accepted:
    """`[reviewed."npm:name"]` tables: the signals accepted, and why."""

    tables = cast(dict[str, Any], tomllib.loads(text).get("reviewed") or {})
    accepted: Accepted = {}
    for key, table in tables.items():
        entry = cast(dict[str, Any], table)
        codes = entry.get("signals")
        reason = entry.get("reason")
        if (
            not isinstance(codes, list)
            or not codes
            or not isinstance(reason, str)
            or not reason.strip()
        ):
            raise ValueError(f"{key}: an exception needs its signals and a reason")
        accepted[key] = (
            frozenset(str(code) for code in cast(list[object], codes)),
            reason.strip(),
        )
    return accepted


def known_names(base: set[Dependency]) -> dict[str, frozenset[str]]:
    """Per ecosystem: the popular names and every name the base already declares."""

    used = {
        ecosystem: frozenset(d.name for d in base if d.ecosystem == ecosystem)
        for ecosystem in (NPM, PYPI)
    }
    return {NPM: POPULAR_NPM | used[NPM], PYPI: POPULAR_PYPI | used[PYPI]}


def review(
    new: list[Dependency],
    base: set[Dependency],
    fetch: Fetch,
    now: datetime.datetime,
) -> Measured:
    known = known_names(base)
    measured: Measured = []
    for dependency in new:
        # One installed from elsewhere is not on the registry to measure.
        from_registry = dependency.origin == REGISTRY
        facts = measure(dependency, fetch) if from_registry else PackageFacts(False)
        pool = known[dependency.ecosystem]
        measured.append((dependency, facts, signals(dependency, facts, now, pool)))
    return measured


def unaccepted_failures(measured: Measured, accepted: Accepted) -> int:
    count = 0
    for dependency, _, found in measured:
        codes = accepted.get(dependency.key, (frozenset[str](), ""))[0]
        count += sum(1 for s in found if s.level == FAIL and s.code not in codes)
    return count


def main(
    arguments: Sequence[str] | None = None,
    fetch: Fetch = https_fetch,
    now: datetime.datetime | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description="A pull request's new direct dependencies, on their registries."
    )
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--head", type=Path, default=Path())
    parser.add_argument("--reviewed", type=Path, default=Path(REVIEWED_FILE))
    parser.add_argument("--summary", type=Path)
    options = parser.parse_args(arguments)
    try:
        base = declared(options.base)
        new = added(base, declared(options.head))
        accepted = reviewed_exceptions(options.reviewed.read_text(encoding="utf-8"))
        measured = review(new, base, fetch, now or datetime.datetime.now(datetime.UTC))
    except (ManifestError, RegistryUnavailable, OSError, ValueError) as error:
        print(f"::error::The new dependencies could not be measured: {error}")
        return EXIT_UNUSABLE

    report = render(measured, accepted)
    print(report)
    print("\n".join(annotations(measured, accepted)))
    if options.summary is not None:
        with options.summary.open("a", encoding="utf-8") as summary:
            summary.write(report)
    failures = unaccepted_failures(measured, accepted)
    if failures:
        print(
            f"{failures} failing signal(s): choose another package, or accept each"
            f" with its reason in {REVIEWED_FILE} after a person checked it."
        )
        return EXIT_FAILED
    return EXIT_PASSED


if __name__ == "__main__":
    sys.exit(main())
