"""
Registry documents for the tests of the registry check of new dependencies
(tests/platform/test_dependency_registry_review.py): npm's and PyPI's JSON
as they answer, cut to the fields the check reads, and a fake registry
that answers from them (no network in tests).
"""

import json
from pathlib import Path
from typing import Any, cast

NOW_ISO: str = "2026-11-03T12:00:00+00:00"

# An npm package two years old, three maintainers, released last month.
NPM_WELL_KEPT: dict[str, Any] = {
    "name": "left-trim",
    "dist-tags": {"latest": "2.1.0"},
    "time": {
        "created": "2024-10-01T10:00:00.000Z",
        "modified": "2026-10-02T10:00:00.000Z",
        "2.1.0": "2026-10-02T10:00:00.000Z",
    },
    "maintainers": [{"name": "a"}, {"name": "b"}, {"name": "c"}],
    "license": "MIT",
    "repository": {
        "type": "git",
        "url": "git+https://github.com/example/left-trim.git",
    },
    "versions": {"2.1.0": {"license": "MIT", "scripts": {"test": "node test.js"}}},
}

# An npm package published nine days ago by one account, with an install script.
NPM_FRESH: dict[str, Any] = {
    "name": "fresh-helper",
    "dist-tags": {"latest": "0.0.2"},
    "time": {
        "created": "2026-10-25T08:00:00.000Z",
        "0.0.2": "2026-10-25T09:00:00.000Z",
    },
    "maintainers": [{"name": "solo"}],
    "versions": {"0.0.2": {"scripts": {"postinstall": "node setup.js"}}},
}

# A deprecated npm package with no release in three years.
NPM_DEPRECATED: dict[str, Any] = {
    "name": "old-request",
    "dist-tags": {"latest": "1.0.0"},
    "time": {
        "created": "2015-01-01T00:00:00.000Z",
        "1.0.0": "2023-06-01T00:00:00.000Z",
    },
    "maintainers": [{"name": "a"}, {"name": "b"}],
    "license": "Apache-2.0",
    "repository": "github:example/old-request",
    "versions": {
        "1.0.0": {"deprecated": "Use fetch instead.", "hasInstallScript": True}
    },
}


def pypi_file(
    day: str, *, kind: str = "bdist_wheel", yanked: bool = False
) -> dict[str, Any]:
    return {
        "upload_time_iso_8601": f"{day}T10:00:00.000000Z",
        "packagetype": kind,
        "yanked": yanked,
    }


# A PyPI project from 2020, two owners, a wheel in its latest release.
PYPI_WELL_KEPT: dict[str, Any] = {
    "info": {
        "license_expression": "BSD-3-Clause",
        "classifiers": ["Development Status :: 5 - Production/Stable"],
        "project_urls": {
            "Documentation": "https://docs.example",
            "Source": "https://github.com/example/tidy",
        },
    },
    "ownership": {
        "roles": [
            {"role": "Owner", "user": "one"},
            {"role": "Maintainer", "user": "two"},
        ]
    },
    "releases": {"1.0": [pypi_file("2020-05-01")], "2.0": [pypi_file("2026-09-01")]},
    "urls": [pypi_file("2026-09-01"), pypi_file("2026-09-01", kind="sdist")],
}

# An inactive PyPI project: only a source distribution, the licence in a classifier.
PYPI_INACTIVE: dict[str, Any] = {
    "info": {
        "license": "",
        "classifiers": [
            "Development Status :: 7 - Inactive",
            "License :: OSI Approved :: MIT License",
        ],
        "home_page": "https://example.org/sleepy",
    },
    "releases": {"0.1": [pypi_file("2019-01-01", kind="sdist")]},
    "urls": [pypi_file("2019-01-01", kind="sdist")],
}

# Every file of every release yanked; PyPI names no owners.
PYPI_YANKED: dict[str, Any] = {
    "info": {"license": "MIT\nlong text of the licence"},
    "releases": {"0.1": [pypi_file("2025-01-01", yanked=True)]},
    "urls": [],
}


class FakeRegistry:
    """Answers registry addresses from documents; anything else is 404."""

    def __init__(self, documents: dict[str, dict[str, Any]], status: int = 200) -> None:
        self.documents = documents
        self.status = status
        self.asked: list[str] = []

    def __call__(self, address: str) -> tuple[int, bytes]:
        self.asked.append(address)
        if address not in self.documents:
            return 404, b'{"error":"Not found"}'
        return self.status, json.dumps(self.documents[address]).encode()


def toml_value(entry: object) -> str:
    if isinstance(entry, dict):
        table = cast(dict[str, object], entry)
        pairs = ", ".join(
            f"{key} = {json.dumps(value)}" for key, value in table.items()
        )
        return f"{{{pairs}}}"
    return json.dumps(entry)


def write_manifests(
    root: Path,
    npm: dict[str, str],
    python: list[str],
    groups: dict[str, list[object]] | None = None,
) -> Path:
    """A repository root with web/package.json and pyproject.toml declaring these."""

    (root / "web").mkdir(parents=True, exist_ok=True)
    (root / "web" / "package.json").write_text(
        json.dumps({"dependencies": npm}), encoding="utf-8"
    )
    lines = [
        "[project]",
        f"dependencies = {json.dumps(python)}",
        "",
        "[dependency-groups]",
    ]
    for name, entries in (groups or {}).items():
        lines.append(f"{name} = [{', '.join(toml_value(entry) for entry in entries)}]")
    (root / "pyproject.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root
