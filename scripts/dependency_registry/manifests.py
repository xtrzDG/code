"""
The direct dependencies the repository declares, and the ones a pull
request adds: npm's package.json files (the cabinet, the Zapier app, the
Lighthouse tool) and pyproject.toml (the project's dependencies, optional
ones and every dependency group). A name is new when no manifest of its
ecosystem declared it before: moving a package between manifests or
changing its version is not a new dependency.

Where each one is installed from counts too: the registry check measures
the registry, so a dependency installed from elsewhere (a git repository,
an address, a local path, the workspace, another package index) is new
whenever its name or that origin is, and an npm alias (`"x":
"npm:y@1"`) is the package it installs (`y`).
"""

import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

NPM: str = "npm"
PYPI: str = "pypi"
REGISTRY: str = "registry"
# Where a dependency comes from when not from its registry, as the report says it.
ORIGINS: dict[str, str] = {
    "git": "a git repository",
    "url": "an address",
    "path": "a local path",
    "workspace": "the workspace",
    "index": "another package index",
}
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
# PEP 508's direct reference: `name[extras] @ url`.
DIRECT_REFERENCE: re.Pattern[str] = re.compile(r"^[^@;]*@\s*(\S+)")
# npm's specs that do not name a registry version (package.json "dependencies").
NPM_GIT_SPEC: re.Pattern[str] = re.compile(
    r"^(?:git\+|git:|github:|gitlab:|bitbucket:|gist:)|^[\w.-]+/[\w.-]+(?:#.*)?$",
    re.IGNORECASE,
)
NPM_URL_SPEC: re.Pattern[str] = re.compile(r"^https?://", re.IGNORECASE)
NPM_PATH_SPEC: re.Pattern[str] = re.compile(
    r"^(?:file:|link:|portal:|\.{0,2}/|~/)|\.t(?:ar\.)?gz$", re.IGNORECASE
)
NPM_ALIAS: str = "npm:"
UV_SOURCE_KINDS: tuple[str, ...] = ("git", "url", "path", "workspace", "index")


class ManifestError(ValueError):
    """A manifest that cannot be read: nothing can be compared."""


@dataclass(frozen=True, order=True)
class Dependency:
    ecosystem: str
    name: str
    manifest: str
    # REGISTRY, or a key of ORIGINS.
    origin: str = REGISTRY

    @property
    def key(self) -> str:
        """`npm:name` or `pypi:name`, as the reviewed exceptions name it."""

        return f"{self.ecosystem}:{self.name}"


def python_name(name: str) -> str:
    """PEP 503: one spelling per project (lower case, runs of -_. as -)."""

    return re.sub(r"[-_.]+", "-", name).lower()


def npm_origin(spec: str) -> str:
    """Where npm installs a spec from: REGISTRY for a version, range or tag."""

    spec = spec.strip()
    if spec.lower().startswith("workspace:"):
        return "workspace"
    if NPM_URL_SPEC.match(spec):
        return "url"
    if NPM_PATH_SPEC.search(spec):
        return "path"
    if NPM_GIT_SPEC.search(spec):
        return "git"
    return REGISTRY


def npm_alias_target(spec: str) -> str:
    """The package `npm:name@range` installs."""

    target = spec.strip()[len(NPM_ALIAS) :]
    at = target.find("@", 1)
    return target if at < 0 else target[:at]


def npm_dependency(name: str, spec: object, manifest: str) -> Dependency:
    text = spec if isinstance(spec, str) else str(spec)
    if text.strip().lower().startswith(NPM_ALIAS):
        return Dependency(NPM, npm_alias_target(text).lower(), manifest)
    return Dependency(NPM, name.lower(), manifest, npm_origin(text))


def npm_dependencies(text: str, manifest: str) -> set[Dependency]:
    try:
        document = cast(dict[str, Any], json.loads(text))
    except ValueError as error:
        raise ManifestError(f"{manifest}: {error}") from error
    found: set[Dependency] = set()
    for section in NPM_SECTIONS:
        entries = cast(dict[str, object], document.get(section) or {})
        found |= {npm_dependency(n, spec, manifest) for n, spec in entries.items()}
    return found


def reference_origin(address: str) -> str:
    lowered = address.lower()
    if lowered.startswith("git+"):
        return "git"
    return "path" if lowered.startswith("file:") else "url"


def uv_source_origins(document: dict[str, Any]) -> dict[str, str]:
    """`[tool.uv.sources]`: the names uv installs from elsewhere than PyPI."""

    tool = cast(dict[str, Any], document.get("tool") or {})
    uv = cast(dict[str, Any], tool.get("uv") or {})
    origins: dict[str, str] = {}
    for name, source in cast(dict[str, object], uv.get("sources") or {}).items():
        tables = cast(list[object], source) if isinstance(source, list) else [source]
        kinds = {
            key
            for table in tables
            if isinstance(table, dict)
            for key in cast(dict[str, object], table)
        }
        origin = next((kind for kind in UV_SOURCE_KINDS if kind in kinds), "index")
        origins[python_name(name)] = origin
    return origins


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
    sources = uv_source_origins(document)
    found: set[Dependency] = set()
    for requirement in requirements:
        match = REQUIREMENT_NAME.match(str(requirement))
        if match is None:
            continue
        name = python_name(match.group(1))
        reference = DIRECT_REFERENCE.match(str(requirement))
        origin = reference_origin(reference.group(1)) if reference else REGISTRY
        found.add(Dependency(PYPI, name, manifest, sources.get(name, origin)))
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
    """
    The head's dependencies whose name no manifest of theirs had at the
    base, and those now installed from an origin other than the registry
    that the base did not install them from (one entry per name, the one
    from elsewhere first).
    """

    known = {(dependency.ecosystem, dependency.name) for dependency in base}
    origins = {(d.ecosystem, d.name, d.origin) for d in base}
    new: dict[tuple[str, str], Dependency] = {}
    for dependency in sorted(head):
        identity = (dependency.ecosystem, dependency.name)
        elsewhere = dependency.origin != REGISTRY
        moved = elsewhere and (*identity, dependency.origin) not in origins
        if identity in known and not moved:
            continue
        current = new.get(identity)
        if current is None or (current.origin == REGISTRY and elsewhere):
            new[identity] = dependency
    return sorted(new.values())
