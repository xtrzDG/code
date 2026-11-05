"""
Where a new dependency is installed from (SDLC-02,
scripts/dependency_registry/): the registry check measures npm and PyPI, so
a dependency installed from a git repository, an address, a local path, the
workspace or another index is never passed on the registry's facts of its
name. It fails until a person accepts it, also when only its origin
changed; an npm alias is measured as the package it installs. Names in one
npm scope are not lookalikes of each other, and a registry's text cannot
break the report's table. The registries are fakes.
"""

import datetime
from pathlib import Path

from scripts.dependency_registry.manifests import (
    NPM,
    PYPI,
    REGISTRY,
    Dependency,
    added,
    declared,
    npm_dependencies,
    python_dependencies,
)
from scripts.dependency_registry.registry_facts import (
    PackageFacts,
    npm_facts,
    registry_address,
)
from scripts.dependency_registry.report import render
from scripts.dependency_registry.risk_signals import FAIL, lookalike, signals
from scripts.dependency_registry_review import EXIT_FAILED, EXIT_PASSED, main
from tests.platform.dependency_registry_fixtures import (
    NOW_ISO,
    NPM_WELL_KEPT,
    FakeRegistry,
    write_manifests,
)

NOW: datetime.datetime = datetime.datetime.fromisoformat(NOW_ISO)
WEB = "web/package.json"


def origins(found: set[Dependency]) -> dict[str, str]:
    return {dependency.name: dependency.origin for dependency in found}


def test_npm_specs_say_where_a_package_comes_from_and_an_alias_is_its_target() -> None:
    specs = {
        "a": "github:someone/a",
        "b": "someone/b#main",
        "c": "git+https://github.com/someone/c.git",
        "d": "https://example.com/d-1.0.0.tgz",
        "e": "file:../e",
        "f": "./vendor/f.tgz",
        "g": "workspace:*",
        "h": "^1.2.3",
        "i": "latest",
        "j": "1.x || >=2.5.0 <3",
        "alias-one": "npm:@scope/Real-One@^1.0.0",
        "alias-two": "npm:real-two",
    }
    text = "{" + ", ".join(f'"{k}": "{v}"' for k, v in specs.items()) + "}"

    found = origins(npm_dependencies(f'{{"dependencies": {text}}}', WEB))

    assert found == {
        "a": "git",
        "b": "git",
        "c": "git",
        "d": "url",
        "e": "path",
        "f": "path",
        "g": "workspace",
        "h": REGISTRY,
        "i": REGISTRY,
        "j": REGISTRY,
        "@scope/real-one": REGISTRY,
        "real-two": REGISTRY,
    }


def test_python_direct_references_and_uv_sources_come_from_elsewhere() -> None:
    found = python_dependencies(
        "[project]\n"
        'dependencies = ["tidy @ git+https://github.com/someone/tidy",'
        ' "Wheel_Pkg[extra] @ https://example.com/wheel_pkg-1-py3-none-any.whl",'
        ' "local @ file:///src/local", "plain>=1; extra == \\"a@b\\"",'
        ' "forked", "mirrored", "nearby"]\n'
        "[tool.uv.sources]\n"
        'forked = { git = "https://github.com/someone/forked" }\n'
        'mirrored = [{ index = "internal", marker = "sys_platform == \'linux\'" }]\n'
        'nearby = { path = "../nearby", editable = true }\n',
        "pyproject.toml",
    )

    assert origins(found) == {
        "tidy": "git",
        "wheel-pkg": "url",
        "local": "path",
        "plain": REGISTRY,
        "forked": "git",
        "mirrored": "index",
        "nearby": "path",
    }


def test_a_known_name_moved_off_the_registry_is_new_and_wins_over_its_twin(
    tmp_path: Path,
) -> None:
    base = write_manifests(
        tmp_path / "base",
        {"lodash": "^4", "pinned-fork": "github:us/pinned-fork", "zod": "4"},
        ["fastapi"],
    )
    head = write_manifests(
        tmp_path / "head",
        {
            "lodash": "github:someone/lodash",
            "pinned-fork": "github:us/pinned-fork#v2",
            "zod": "npm:zod-next@4",
        },
        ["fastapi"],
    )
    (head / "integrations" / "zapier").mkdir(parents=True)
    (head / "integrations" / "zapier" / "package.json").write_text(
        '{"dependencies": {"left-trim": "2"}}', encoding="utf-8"
    )
    (head / "web" / "package.json").write_text(
        '{"dependencies": {"lodash": "github:someone/lodash", "left-trim":'
        ' "someone/left-trim", "pinned-fork": "github:us/pinned-fork#v2",'
        ' "zod": "npm:zod-next@4"}}',
        encoding="utf-8",
    )

    new = added(declared(base), declared(head))

    # The fork already came from git: a new ref is not a new origin.
    assert [(d.key, d.origin, d.manifest) for d in new] == [
        ("npm:left-trim", "git", WEB),
        ("npm:lodash", "git", WEB),
        ("npm:zod-next", REGISTRY, WEB),
    ]


def test_a_dependency_from_elsewhere_fails_without_asking_the_registry(
    tmp_path: Path,
) -> None:
    base = write_manifests(tmp_path / "base", {"left-trim": "^1"}, ["fastapi"])
    head = write_manifests(
        tmp_path / "head", {"left-trim": "github:someone/left-trim"}, ["fastapi"]
    )
    registry = FakeRegistry(
        {registry_address(Dependency(NPM, "left-trim", WEB)): NPM_WELL_KEPT}
    )

    def check(reviewed: str) -> tuple[int, str]:
        (tmp_path / "reviewed.toml").write_text(reviewed, encoding="utf-8")
        summary = tmp_path / f"summary-{len(reviewed)}.md"
        arguments = ["--base", str(base), "--head", str(head), "--summary"]
        status = main(
            [*arguments, str(summary), "--reviewed", str(tmp_path / "reviewed.toml")],
            fetch=registry,
            now=NOW,
        )
        return status, summary.read_text("utf-8")

    status, summary = check("[reviewed]\n")
    accepted, accepted_summary = check(
        '[reviewed."npm:left-trim"]\nsignals = ["not-from-registry"]\n'
        'reason = "Our fork until the fix is released; pinned to a reviewed commit."\n'
    )

    assert status == EXIT_FAILED
    assert registry.asked == []
    assert (
        "| npm:left-trim | `web/package.json` | installed from a git repository |"
        in summary
    )
    assert "not-from-registry, installed from a git repository" in summary
    assert "**fails**" in summary
    assert accepted == EXIT_PASSED
    assert "(accepted: Our fork until the fix is released" in accepted_summary


def test_the_signal_of_each_origin_fails() -> None:
    for origin in ("git", "url", "path", "workspace", "index"):
        dependency = Dependency(PYPI, "tidy", "pyproject.toml", origin)
        [signal] = signals(dependency, PackageFacts(False), NOW, frozenset())

        assert (signal.code, signal.level) == ("not-from-registry", FAIL), origin
        assert "not from the registry" in signal.text


def test_names_of_one_npm_scope_are_no_lookalikes_but_a_lookalike_scope_is() -> None:
    known = frozenset({"@sentry/node", "@types/qs", "react"})

    # Only Sentry publishes in @sentry, only DefinitelyTyped in @types.
    assert lookalike("@sentry/core", known) is None
    assert lookalike("@types/ws", known) is None
    assert lookalike("@sentri/node", known) == "@sentry/node"
    assert lookalike("raect", known) == "react"


def test_a_registry_s_text_stays_in_its_table_cell() -> None:
    dependency = Dependency(NPM, "left-trim", WEB)
    facts = npm_facts(
        {
            **NPM_WELL_KEPT,
            "license": "MIT\n::error::forged | column",
            "versions": {"2.1.0": {"license": "MIT\n::error::forged | column"}},
        }
    )

    report = render([(dependency, facts, [])], {})

    [line] = [line for line in report.splitlines() if "left-trim" in line]
    assert "MIT ::error::forged \\| column" in line
    assert not any(line.startswith("::") for line in report.splitlines())
