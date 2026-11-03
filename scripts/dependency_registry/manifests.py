"""
The direct dependencies the repository declares, and the ones a pull
request adds: npm's package.json files (the cabinet, the Zapier app, the
Lighthouse tool) and pyproject.toml (the project's dependencies, optional
ones and every dependency group). A name is new when no manifest of its
ecosystem declared it before: moving a package between manifests or
changing its version is not a new dependency.
"""

import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

NPM: str = "npm"
PYPI: str = "pypi"
NPM_MANIFESTS: tuple[str, ...] = (
    "web/package.json",
    "integrations/zapier/package.json",
    ".github/tools/lhci/package.json",
)
PYTHON_MANIFESTS: tuple[str, ...] = ("pyproject.toml",)
NPM_SECTIONS: tuple[str, ...] = (
    "dependencies",
    "devDependencies",
    "optionalDependencies",
    "peerDependencies",
)
# PEP 508: the name a requirement starts with.
REQUIREMENT_NAME: re.Pattern[str] = re.compile(
    r"^\s*([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)"
)


class ManifestError(ValueError):
    """A manifest that cannot be read: nothing can be compared."""


@dataclass(frozen=True, order=True)
class Dependency:
    ecosystem: str
    name: str
    manifest: str

    @property
    def key(self) -> str:
        """`npm:name` or `pypi:name`, as the reviewed exceptions name it."""

        return f"{self.ecosystem}:{self.name}"


def python_name(name: str) -> str:
    """PEP 503: one spelling per project (lower case, runs of -_. as -)."""

    return re.sub(r"[-_.]+", "-", name).lower()


def npm_dependencies(text: str, manifest: str) -> set[Dependency]:
    try:
        document = cast(dict[str, Any], json.loads(text))
    except ValueError as error:
        raise ManifestError(f"{manifest}: {error}") from error
    names: set[str] = set()
    for section in NPM_SECTIONS:
        names |= set(cast(dict[str, Any], document.get(section) or {}))
    return {Dependency(NPM, name.lower(), manifest) for name in names}


def python_dependencies(text: str, manifest: str) -> set[Dependency]:
    try:
        document = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise ManifestError(f"{manifest}: {error}") from error
    project = cast(dict[str, Any], document.get("project") or {})
    requirements: list[object] = list(project.get("dependencies") or [])
    for extra in cast(
        dict[str, list[object]], project.get("optional-dependencies") or {}
    ).values():
        requirements.extend(extra)
    for group in cast(
        dict[str, list[object]], document.get("dependency-groups") or {}
    ).values():
        # A group may include another one ({include-group = "..."}): not a package.
        requirements.extend(entry for entry in group if isinstance(entry, str))
    found: set[Dependency] = set()
    for requirement in requirements:
        match = REQUIREMENT_NAME.match(str(requirement))
        if match is not None:
            found.add(Dependency(PYPI, python_name(match.group(1)), manifest))
    return found


def declared(root: Path) -> set[Dependency]:
    """Every direct dependency the manifests under `root` declare."""

    found: set[Dependency] = set()
    for manifest in NPM_MANIFESTS:
        path = root / manifest
        if path.is_file():
            found |= npm_dependencies(path.read_text(encoding="utf-8"), manifest)
    for manifest in PYTHON_MANIFESTS:
        path = root / manifest
        if path.is_file():
            found |= python_dependencies(path.read_text(encoding="utf-8"), manifest)
    return found


def added(base: set[Dependency], head: set[Dependency]) -> list[Dependency]:
    """The head's dependencies whose name no manifest of theirs had at the base."""

    known = {(dependency.ecosystem, dependency.name) for dependency in base}
    new: dict[tuple[str, str], Dependency] = {}
    for dependency in sorted(head):
        identity = (dependency.ecosystem, dependency.name)
        if identity not in known:
            new.setdefault(identity, dependency)
    return sorted(new.values())
