"""
The signals a new dependency's registry facts raise. Failing ones stop the
pull request until a person accepted them in
.github/dependency-registry-review.toml (with the reason):

- not-found: no such package on the registry (a typo, a name a model made
  up, or an internal name an attacker could register);
- closed: deprecated, archived, quarantined, or every release yanked;
- too-new: first released fewer than 30 days ago (most malicious packages
  are found and removed within days);
- typosquat: one or two characters, or only separators, from a popular
  name or one the repository already uses (npm names of one scope are
  not compared with each other: only the scope's owner publishes in it);
- not-from-registry: installed from a git repository, an address, a local
  path, the workspace or another index, so the registry's facts say
  nothing about what is installed.

Warnings go into the report for the reviewer: younger than 180 days, no
release in two years, a single account that may publish it, code that
runs on install (npm scripts, a PyPI release without a wheel), no licence
or no source repository named.
"""

import datetime
from dataclasses import dataclass

from scripts.dependency_registry.manifests import ORIGINS, REGISTRY, Dependency
from scripts.dependency_registry.registry_facts import PackageFacts

FAIL: str = "fail"
WARN: str = "warn"
TOO_NEW_DAYS: int = 30
YOUNG_DAYS: int = 180
STALE_DAYS: int = 730
# Names this short are too close to too many others to compare.
SHORTEST_COMPARED_NAME: int = 4
# Up to this length one edit makes a lookalike; longer names, two.
ONE_EDIT_LENGTH: int = 7


@dataclass(frozen=True)
class Signal:
    code: str
    level: str
    text: str


def edit_distance(left: str, right: str) -> int:
    """Optimal string alignment: insertions, deletions, substitutions, swaps."""

    rows = [[0] * (len(right) + 1) for _ in range(len(left) + 1)]
    for i in range(len(left) + 1):
        rows[i][0] = i
    for j in range(len(right) + 1):
        rows[0][j] = j
    for i in range(1, len(left) + 1):
        for j in range(1, len(right) + 1):
            cost = 0 if left[i - 1] == right[j - 1] else 1
            rows[i][j] = min(
                rows[i - 1][j] + 1, rows[i][j - 1] + 1, rows[i - 1][j - 1] + cost
            )
            if (
                i > 1
                and j > 1
                and left[i - 1] == right[j - 2]
                and left[i - 2] == right[j - 1]
            ):
                rows[i][j] = min(rows[i][j], rows[i - 2][j - 2] + 1)
    return rows[len(left)][len(right)]


def bare(name: str) -> str:
    return name.replace("-", "").replace("_", "").replace(".", "")


def scope(name: str) -> str | None:
    """An npm name's scope (`@types` of `@types/node`), None without one."""

    return name.split("/", 1)[0] if name.startswith("@") and "/" in name else None


def lookalike(name: str, known: frozenset[str]) -> str | None:
    """The known name `name` imitates, if any; a known name imitates nothing."""

    if name in known:
        return None
    allowed = 1 if len(name) <= ONE_EDIT_LENGTH else 2
    own_scope = scope(name)
    for other in sorted(known):
        if len(other) < SHORTEST_COMPARED_NAME:
            continue
        if own_scope is not None and scope(other) == own_scope:
            # Only the scope's owner publishes in it: no one can squat there.
            continue
        if bare(other) == bare(name) or edit_distance(name, other) <= allowed:
            return other
    return None


def age_signals(facts: PackageFacts, now: datetime.datetime) -> list[Signal]:
    if facts.first_release is None:
        return [Signal("age-unknown", WARN, "the registry names no first release")]
    signals: list[Signal] = []
    age = (now - facts.first_release).days
    if age < TOO_NEW_DAYS:
        signals.append(Signal("too-new", FAIL, f"first released {age} days ago"))
    elif age < YOUNG_DAYS:
        signals.append(Signal("young", WARN, f"first released {age} days ago"))
    if facts.latest_release is not None:
        idle = (now - facts.latest_release).days
        if idle > STALE_DAYS:
            signals.append(Signal("unmaintained", WARN, f"no release in {idle} days"))
    return signals


def signals(
    dependency: Dependency,
    facts: PackageFacts,
    now: datetime.datetime,
    known: frozenset[str],
) -> list[Signal]:
    if dependency.origin != REGISTRY:
        where = ORIGINS.get(dependency.origin, dependency.origin)
        text = f"installed from {where}, not from the registry: nothing measured"
        return [Signal("not-from-registry", FAIL, text)]
    if not facts.exists:
        return [
            Signal("not-found", FAIL, f"no package {dependency.name} on the registry")
        ]
    found: list[Signal] = []
    imitated = lookalike(dependency.name, known)
    if imitated is not None:
        found.append(Signal("typosquat", FAIL, f"looks like {imitated}"))
    if facts.closed:
        found.append(Signal("closed", FAIL, "deprecated, archived or yanked"))
    found.extend(age_signals(facts, now))
    if facts.publishers == 1:
        found.append(Signal("single-publisher", WARN, "one account may publish it"))
    if facts.runs_code_on_install:
        found.append(Signal("install-code", WARN, "installing it runs its own code"))
    if facts.licence is None:
        found.append(Signal("no-licence", WARN, "the registry names no licence"))
    if facts.repository is None:
        found.append(
            Signal("no-source", WARN, "the registry names no source repository")
        )
    return found
