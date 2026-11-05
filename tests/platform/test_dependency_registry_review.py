"""
The registry check of new dependencies (SDLC-02, scripts/dependency_registry/):
which direct dependencies a pull request adds, what npm's and PyPI's
documents say about each (fixtures, never the network), and the signals
those facts raise.
"""

import datetime
from pathlib import Path

import pytest

from scripts.dependency_registry.manifests import (
    NPM,
    PYPI,
    Dependency,
    ManifestError,
    added,
    declared,
    npm_dependencies,
    python_dependencies,
)
from scripts.dependency_registry.registry_facts import (
    PackageFacts,
    RegistryUnavailable,
    measure,
    npm_facts,
    pypi_facts,
    registry_address,
)
from scripts.dependency_registry.risk_signals import (
    FAIL,
    WARN,
    Signal,
    edit_distance,
    lookalike,
    signals,
)
from tests.platform.dependency_registry_fixtures import (
    NOW_ISO,
    NPM_DEPRECATED,
    NPM_FRESH,
    NPM_WELL_KEPT,
    PYPI_INACTIVE,
    PYPI_WELL_KEPT,
    PYPI_YANKED,
    FakeRegistry,
    write_manifests,
)

NOW: datetime.datetime = datetime.datetime.fromisoformat(NOW_ISO)
KNOWN: frozenset[str] = frozenset({"requests", "react", "react-dom", "typescript"})


def day(text: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(f"{text}T10:00:00+00:00")


def test_every_npm_section_and_every_python_group_declares_dependencies() -> None:
    npm = npm_dependencies(
        '{"dependencies": {"Next": "16"}, "devDependencies": {"vitest": "5"},'
        ' "optionalDependencies": {"fsevents": "2"},'
        ' "peerDependencies": {"react": "19"}}',
        "web/package.json",
    )
    python = python_dependencies(
        '[project]\ndependencies = ["FastAPI>=0.1", "uvicorn[standard]"]\n'
        "[project.optional-dependencies]\nfast = [\"orjson; python_version>'3'\"]\n"
        '[dependency-groups]\ndev = ["Typing_Extensions", {include-group = "lint"}]\n'
        'lint = ["ruff"]\n',
        "pyproject.toml",
    )

    assert {d.name for d in npm} == {"next", "vitest", "fsevents", "react"}
    assert {d.name for d in python} == {
        "fastapi",
        "uvicorn",
        "orjson",
        "typing-extensions",
        "ruff",
    }
    assert Dependency(PYPI, "ruff", "pyproject.toml").key == "pypi:ruff"


def test_a_manifest_that_cannot_be_read_stops_the_check() -> None:
    with pytest.raises(ManifestError, match="web/package.json"):
        npm_dependencies("{not json", "web/package.json")
    with pytest.raises(ManifestError, match="pyproject.toml"):
        python_dependencies("[project\n", "pyproject.toml")


def test_only_names_no_manifest_declared_before_are_new(tmp_path: Path) -> None:
    base = write_manifests(
        tmp_path / "base",
        {"react": "19", "zod": "4"},
        ["fastapi>=0.1"],
        {"dev": ["pytest"]},
    )
    head = write_manifests(
        tmp_path / "head",
        {"react": "20", "left-trim": "2"},
        ["FastAPI>=0.2", "pytest", "tidy==2"],
        {"dev": [{"include-group": "lint"}], "lint": ["ruff"]},
    )
    (head / "integrations" / "zapier").mkdir(parents=True)
    (head / "integrations" / "zapier" / "package.json").write_text(
        '{"dependencies": {"zod": "4"}}', encoding="utf-8"
    )

    new = added(declared(base), declared(head))

    # A version change, a package moved between manifests or groups, a
    # removal and a manifest spelling change are not new dependencies.
    assert [d.key for d in new] == ["npm:left-trim", "pypi:ruff", "pypi:tidy"]
    assert declared(tmp_path / "nothing") == set()


def test_npm_facts_are_read_from_the_registry_document() -> None:
    kept = npm_facts(NPM_WELL_KEPT)
    fresh = npm_facts(NPM_FRESH)
    deprecated = npm_facts(NPM_DEPRECATED)

    assert kept == PackageFacts(
        exists=True,
        first_release=datetime.datetime(2024, 10, 1, 10, tzinfo=datetime.UTC),
        latest_release=datetime.datetime(2026, 10, 2, 10, tzinfo=datetime.UTC),
        publishers=3,
        closed=False,
        runs_code_on_install=False,
        licence="MIT",
        repository="git+https://github.com/example/left-trim.git",
    )
    assert (fresh.publishers, fresh.runs_code_on_install) == (1, True)
    assert (fresh.licence, fresh.repository) == (None, None)
    assert deprecated.closed and deprecated.runs_code_on_install
    assert deprecated.repository == "github:example/old-request"


def test_pypi_facts_are_read_from_the_registry_document() -> None:
    kept = pypi_facts(PYPI_WELL_KEPT)
    inactive = pypi_facts(PYPI_INACTIVE)
    yanked = pypi_facts(PYPI_YANKED)

    assert kept == PackageFacts(
        exists=True,
        first_release=day("2020-05-01"),
        latest_release=day("2026-09-01"),
        publishers=2,
        closed=False,
        runs_code_on_install=False,
        licence="BSD-3-Clause",
        repository="https://github.com/example/tidy",
    )
    assert inactive.closed and inactive.runs_code_on_install
    assert inactive.licence == "MIT License"
    assert inactive.repository == "https://example.org/sleepy"
    assert inactive.publishers is None
    assert yanked.closed and yanked.licence == "MIT"
    assert yanked.runs_code_on_install is False


def test_the_registry_is_asked_at_its_own_address_and_a_missing_name_is_a_fact() -> (
    None
):
    scoped = Dependency(NPM, "@scope/left-trim", "web/package.json")
    tidy = Dependency(PYPI, "tidy", "pyproject.toml")
    registry = FakeRegistry({registry_address(tidy): PYPI_WELL_KEPT})

    assert registry_address(scoped) == "https://registry.npmjs.org/@scope%2Fleft-trim"
    assert registry_address(tidy) == "https://pypi.org/pypi/tidy/json"
    assert measure(tidy, registry).publishers == 2
    assert measure(scoped, registry) == PackageFacts(exists=False)
    assert registry.asked == [registry_address(tidy), registry_address(scoped)]


def test_a_registry_that_does_not_answer_measures_nothing() -> None:
    tidy = Dependency(PYPI, "tidy", "pyproject.toml")

    def broken(address: str) -> tuple[int, bytes]:
        raise OSError("connection reset")

    with pytest.raises(RegistryUnavailable, match="connection reset"):
        measure(tidy, broken)
    with pytest.raises(RegistryUnavailable, match="HTTP 503"):
        measure(tidy, FakeRegistry({registry_address(tidy): {}}, status=503))
    with pytest.raises(RegistryUnavailable, match="not JSON"):
        measure(tidy, lambda address: (200, b"<html>"))


def test_lookalikes_of_known_names_are_typosquats() -> None:
    assert edit_distance("reqeusts", "requests") == 1
    assert edit_distance("kitten", "sitting") == 3
    assert lookalike("reqeusts", KNOWN) == "requests"
    assert lookalike("raect", KNOWN) == "react"
    assert lookalike("type-script", KNOWN) == "typescript"
    assert lookalike("typescirpt", KNOWN) == "typescript"
    # A known name, a short one, and a different name are no lookalikes.
    assert lookalike("react-dom", KNOWN) is None
    assert lookalike("left-trim", KNOWN) is None
    assert lookalike("rect", frozenset({"rec"})) is None


def codes(found: list[Signal]) -> list[tuple[str, str]]:
    return [(signal.code, signal.level) for signal in found]


def test_the_signals_of_each_package() -> None:
    def of(name: str, facts: PackageFacts) -> list[tuple[str, str]]:
        dependency = Dependency(NPM, name, "web/package.json")
        return codes(signals(dependency, facts, NOW, KNOWN))

    assert of("left-trim", npm_facts(NPM_WELL_KEPT)) == []
    assert of("fresh-helper", npm_facts(NPM_FRESH)) == [
        ("too-new", FAIL),
        ("single-publisher", WARN),
        ("install-code", WARN),
        ("no-licence", WARN),
        ("no-source", WARN),
    ]
    assert of("old-request", npm_facts(NPM_DEPRECATED)) == [
        ("closed", FAIL),
        ("unmaintained", WARN),
        ("install-code", WARN),
    ]
    assert of("reqeusts", npm_facts(NPM_WELL_KEPT)) == [("typosquat", FAIL)]
    assert of("ghost", PackageFacts(exists=False)) == [("not-found", FAIL)]
    young = PackageFacts(
        exists=True, first_release=day("2026-07-01"), licence="MIT", repository="x"
    )
    assert of("left-trim", young) == [("young", WARN)]
    assert of(
        "left-trim", PackageFacts(exists=True, licence="MIT", repository="x")
    ) == [("age-unknown", WARN)]
