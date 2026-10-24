"""
The enum values of every stored document, from the recorded shapes in
tests/storage/document_schemas: now, at a git commit, and as the snapshot of
the last release (tests/storage/release_enums.json) that
tests/architecture_policy/test_enum_values_are_known_one_release_ahead.py
compares them with.
"""

import json
import subprocess  # nosec B404 - git, with fixed arguments
from collections.abc import Iterator
from pathlib import Path
from typing import cast

from tests.storage.document_evolution.evolution_files import (
    SCHEMA_DIRECTORY,
    STORAGE_TESTS_DIRECTORY,
)

SNAPSHOT_PATH: Path = STORAGE_TESTS_DIRECTORY / "release_enums.json"
SCHEMA_PATH_IN_GIT: str = "tests/storage/document_schemas"
PROJECT_ROOT: Path = STORAGE_TESTS_DIRECTORY.parents[1]

# document type -> enum path -> its values
type DocumentEnums = dict[str, dict[str, list[str]]]


def enum_paths(node: object, prefix: str = "") -> Iterator[tuple[str, list[str]]]:
    """(path, values) of every enum of a recorded shape, in the gates' paths."""

    if not isinstance(node, dict):
        return

    shape = cast(dict[str, object], node)
    values: object = shape.get("enum")
    if isinstance(values, list) and prefix:
        yield prefix, sorted(str(value) for value in cast(list[object], values))

    properties: object = shape.get("properties")
    if isinstance(properties, dict):
        for name, child in cast(dict[str, object], properties).items():
            yield from enum_paths(child, f"{prefix}.{name}" if prefix else name)
    yield from enum_paths(shape.get("items"), f"{prefix}[]")
    yield from enum_paths(shape.get("additionalProperties"), f"{prefix}{{}}")
    for key in ("anyOf", "oneOf", "allOf"):
        variants: object = shape.get(key)
        if isinstance(variants, list):
            for variant in cast(list[object], variants):
                yield from enum_paths(variant, prefix)


def enums_of_schema_text(text: str) -> tuple[str, dict[str, list[str]]]:
    """The document type a recorded shape describes and its enums by path."""

    recorded = cast(dict[str, object], json.loads(text))
    enums: dict[str, set[str]] = {}
    for path, values in enum_paths(recorded["shape"]):
        enums.setdefault(path, set()).update(values)
    return str(recorded["document_type"]), {
        path: sorted(values) for path, values in sorted(enums.items())
    }


def current_enums() -> DocumentEnums:
    """The enums of this checkout's recorded shapes."""

    return dict(
        enums_of_schema_text(path.read_text(encoding="utf-8"))
        for path in sorted(SCHEMA_DIRECTORY.glob("*.json"))
    )


def git(*arguments: str) -> str:
    return subprocess.run(  # nosec B603 B607 - git with fixed arguments
        ["git", *arguments],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def enums_at(commit: str) -> DocumentEnums:
    """The enums of the recorded shapes at a commit."""

    names: list[str] = git(
        "ls-tree", "--name-only", commit, f"{SCHEMA_PATH_IN_GIT}/"
    ).split()
    return dict(
        enums_of_schema_text(git("show", f"{commit}:{name}"))
        for name in sorted(names)
        if name.endswith(".json")
    )


def load_snapshot() -> dict[str, object]:
    return cast(dict[str, object], json.loads(SNAPSHOT_PATH.read_text("utf-8")))


def snapshot_enums() -> DocumentEnums:
    return cast(DocumentEnums, load_snapshot()["documents"])
