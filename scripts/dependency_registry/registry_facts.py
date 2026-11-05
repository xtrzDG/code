"""
What a package's registry says about it, measured rather than guessed:
when it was first and last released, how many accounts may publish it,
whether it is deprecated, archived or yanked, whether installing it runs
its own code, its licence and its source repository.

- npm: https://registry.npmjs.org/<name> (`time`, `maintainers`, the latest
  version's `deprecated`, install scripts and `hasInstallScript`);
- PyPI: https://pypi.org/pypi/<name>/json (every file's upload time and
  `yanked`, the owners and maintainers of `ownership` where PyPI publishes
  them, the "Inactive" classifier and the project status; a latest release
  without a wheel means building it runs the package's code).

A value the registry does not publish stays None ("not measured").
"""

import datetime
import http.client
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast
from urllib.parse import quote, urlsplit

from scripts.dependency_registry.manifests import NPM, Dependency

TIMEOUT_SECONDS: float = 20.0
# Large enough for the documents of most packages; a bigger one is read up to here.
LARGEST_DOCUMENT_BYTES: int = 64 * 1024 * 1024
INSTALL_SCRIPTS: tuple[str, ...] = ("preinstall", "install", "postinstall")
INACTIVE_CLASSIFIER: str = "Development Status :: 7 - Inactive"
CLOSED_STATUSES: frozenset[str] = frozenset({"archived", "quarantined", "deprecated"})
SOURCE_LINK_NAMES: tuple[str, ...] = (
    "source",
    "repository",
    "code",
    "github",
    "homepage",
)

# (address) -> (HTTP status, body): https only, no redirect followed.
type Fetch = Callable[[str], tuple[int, bytes]]


class RegistryUnavailable(RuntimeError):
    """The registry did not answer: the package was not measured."""


@dataclass(frozen=True)
class PackageFacts:
    exists: bool
    first_release: datetime.datetime | None = None
    latest_release: datetime.datetime | None = None
    publishers: int | None = None
    closed: bool = False
    runs_code_on_install: bool | None = None
    licence: str | None = None
    repository: str | None = None


def https_fetch(address: str) -> tuple[int, bytes]:
    parts = urlsplit(address)
    connection = http.client.HTTPSConnection(parts.netloc, timeout=TIMEOUT_SECONDS)
    try:
        connection.request(
            "GET",
            parts.path,
            headers={"Accept": "application/json", "User-Agent": "dependency-review"},
        )
        answer = connection.getresponse()
        return answer.status, answer.read(LARGEST_DOCUMENT_BYTES)
    finally:
        connection.close()


def registry_address(dependency: Dependency) -> str:
    if dependency.ecosystem == NPM:
        return f"https://registry.npmjs.org/{quote(dependency.name, safe='@')}"
    return f"https://pypi.org/pypi/{quote(dependency.name)}/json"


def moment(value: object) -> datetime.datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=datetime.UTC)


def text_or_url(value: object) -> str | None:
    """npm writes a licence or repository as text or as {type, url}."""

    if isinstance(value, dict):
        entry = cast(dict[str, Any], value)
        value = entry.get("url") or entry.get("type")
    return str(value) if isinstance(value, str) and value else None


def npm_facts(document: dict[str, Any]) -> PackageFacts:
    times = cast(dict[str, str], document.get("time") or {})
    latest_version = str(
        cast(dict[str, Any], document.get("dist-tags") or {}).get("latest", "")
    )
    versions = cast(dict[str, dict[str, Any]], document.get("versions") or {})
    latest = versions.get(latest_version, {})
    scripts = cast(dict[str, str], latest.get("scripts") or {})
    maintainers = document.get("maintainers")
    return PackageFacts(
        exists=True,
        first_release=moment(times.get("created")),
        latest_release=moment(times.get(latest_version) or times.get("modified")),
        publishers=len(cast(list[object], maintainers))
        if isinstance(maintainers, list)
        else None,
        closed=bool(latest.get("deprecated")) or "unpublished" in times or not latest,
        runs_code_on_install=bool(latest.get("hasInstallScript"))
        or any(name in scripts for name in INSTALL_SCRIPTS),
        licence=text_or_url(latest.get("license") or document.get("license")),
        repository=text_or_url(document.get("repository")),
    )


def pypi_publishers(document: dict[str, Any]) -> int | None:
    ownership = document.get("ownership")
    if not isinstance(ownership, dict):
        return None
    roles = cast(dict[str, Any], ownership).get("roles")
    if not isinstance(roles, list):
        return None
    users = {
        str(cast(dict[str, Any], role).get("user"))
        for role in cast(list[object], roles)
        if isinstance(role, dict)
    }
    return len(users)


def pypi_status(info: dict[str, Any], document: dict[str, Any]) -> str:
    for status in (info.get("project_status"), document.get("project-status")):
        if isinstance(status, dict):
            status = cast(dict[str, Any], status).get("status")
        if isinstance(status, str) and status:
            return status.lower()
    return "active"


def pypi_source(info: dict[str, Any]) -> str | None:
    links = cast(dict[str, str], info.get("project_urls") or {})
    for wanted in SOURCE_LINK_NAMES:
        for label, address in links.items():
            if wanted in label.lower() and address:
                return address
    return text_or_url(info.get("home_page"))


def pypi_licence(info: dict[str, Any]) -> str | None:
    expression = text_or_url(info.get("license_expression"))
    if expression:
        return expression
    declared = text_or_url(info.get("license"))
    if declared:
        return declared.splitlines()[0][:80]
    classifiers = cast(list[str], info.get("classifiers") or [])
    return next(
        (
            entry.split(" :: ")[-1]
            for entry in classifiers
            if entry.startswith("License ::")
        ),
        None,
    )


def pypi_facts(document: dict[str, Any]) -> PackageFacts:
    info = cast(dict[str, Any], document.get("info") or {})
    releases = cast(dict[str, list[dict[str, Any]]], document.get("releases") or {})
    files = [file for release in releases.values() for file in release]
    uploads = [
        stamp
        for file in files
        if (stamp := moment(file.get("upload_time_iso_8601"))) is not None
    ]
    latest_files = cast(list[dict[str, Any]], document.get("urls") or [])
    classifiers = cast(list[str], info.get("classifiers") or [])
    every_file_yanked = bool(files) and all(bool(file.get("yanked")) for file in files)
    return PackageFacts(
        exists=True,
        first_release=min(uploads, default=None),
        latest_release=max(uploads, default=None),
        publishers=pypi_publishers(document),
        closed=every_file_yanked
        or INACTIVE_CLASSIFIER in classifiers
        or pypi_status(info, document) in CLOSED_STATUSES,
        runs_code_on_install=bool(latest_files)
        and not any(file.get("packagetype") == "bdist_wheel" for file in latest_files),
        licence=pypi_licence(info),
        repository=pypi_source(info),
    )


def measure(dependency: Dependency, fetch: Fetch) -> PackageFacts:
    """The registry's facts; a missing name is a fact too (it does not exist there)."""

    address = registry_address(dependency)
    try:
        status, body = fetch(address)
    except (OSError, http.client.HTTPException) as error:
        raise RegistryUnavailable(f"{address}: {error}") from error
    if status == 404:
        return PackageFacts(exists=False)
    if status != 200:
        raise RegistryUnavailable(f"{address}: HTTP {status}")
    try:
        document = cast(dict[str, Any], json.loads(body))
    except ValueError as error:
        raise RegistryUnavailable(f"{address}: not JSON ({error})") from error
    return npm_facts(document) if dependency.ecosystem == NPM else pypi_facts(document)
