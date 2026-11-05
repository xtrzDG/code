"""
Golden fixtures and schema snapshots of the stored document types.

- `tests/storage/golden/<collection>/v<N>.json`: one document as release
  shape N wrote it. Never edited or deleted while rows of that version may
  exist: the current code must keep reading it.
- `tests/storage/document_schemas/<DocumentType>.json`: the stored shape of
  the current version (`model_json_schema()` with `$ref`s inlined and
  titles, descriptions and examples dropped, so only the data shape counts)
  and the version it belongs to.

`python -m tests.storage.document_evolution.refresh` writes both;
tests/architecture_policy/test_document_evolution.py enforces them.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from base_pydantic_schemas import PersistentDocument

from app.adapters.storage.document_upgrades import StoredJsonObject
from app.adapters.storage.persisted_document_codec import parse_stored_object
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName

STORAGE_TESTS_DIRECTORY: Path = Path(__file__).resolve().parents[1]
GOLDEN_DIRECTORY: Path = STORAGE_TESTS_DIRECTORY / "golden"
SCHEMA_DIRECTORY: Path = STORAGE_TESTS_DIRECTORY / "document_schemas"
GOLDEN_FILE_PATTERN: re.Pattern[str] = re.compile(r"^v([1-9][0-9]*)\.json$")
# Schema keywords that describe rather than constrain the data.
ANNOTATION_KEYWORDS: frozenset[str] = frozenset({"title", "description", "examples"})
# Keywords whose value maps names (fields, definitions) to schemas.
NAMED_SCHEMA_KEYWORDS: frozenset[str] = frozenset({"properties", "$defs"})

type JsonValue = object


def stored_shape(document_type: type[PersistentDocument]) -> JsonValue:
    """The data shape of a document type, independent of names and prose."""

    schema: dict[str, JsonValue] = document_type.model_json_schema()
    return normalize(schema, as_object(schema.get("$defs", {})), ())


def as_object(node: JsonValue) -> dict[str, JsonValue]:
    assert isinstance(node, dict)
    # JSON schema objects always have string keys.
    return cast(dict[str, JsonValue], node)


def normalize(
    node: JsonValue,
    definitions: dict[str, JsonValue],
    expanding: tuple[str, ...],
) -> JsonValue:
    """Inline `$ref`s (a cycle keeps its ref), drop annotations and `$defs`."""

    if isinstance(node, list):
        items: list[JsonValue] = cast(list[JsonValue], node)
        return [normalize(item, definitions, expanding) for item in items]

    if not isinstance(node, dict):
        return node

    schema: dict[str, JsonValue] = cast(dict[str, JsonValue], node)
    reference: JsonValue = schema.get("$ref")
    if isinstance(reference, str) and reference.startswith("#/$defs/"):
        name: str = reference.removeprefix("#/$defs/")
        if name not in expanding:
            siblings: dict[str, JsonValue] = {
                key: value for key, value in schema.items() if key != "$ref"
            }
            inlined = as_object(
                normalize(definitions[name], definitions, (*expanding, name))
            )
            return {**inlined, **as_object(normalize(siblings, definitions, expanding))}

    normalized: dict[str, JsonValue] = {}
    for keyword, value in schema.items():
        if keyword in ANNOTATION_KEYWORDS or keyword == "$defs":
            continue

        if keyword in NAMED_SCHEMA_KEYWORDS:
            normalized[keyword] = {
                name: normalize(member, definitions, expanding)
                for name, member in as_object(value).items()
            }
        else:
            normalized[keyword] = normalize(value, definitions, expanding)

    return normalized


@dataclass(frozen=True)
class EvolutionFiles:
    """Where the golden fixtures and snapshots live (the repository's, or a
    temporary copy in tests of the refresh tool)."""

    golden_directory: Path = GOLDEN_DIRECTORY
    schema_directory: Path = SCHEMA_DIRECTORY

    def snapshot_path(self, document_type: type[PersistentDocument]) -> Path:
        return self.schema_directory / f"{document_type.__name__}.json"

    def golden_path(
        self, collection_name: DocumentCollectionName, version: int
    ) -> Path:
        return self.golden_directory / str(collection_name) / f"v{version}.json"

    def golden_versions(self, collection_name: DocumentCollectionName) -> list[int]:
        """Versions with a golden fixture, ascending."""

        directory: Path = self.golden_directory / str(collection_name)
        if not directory.is_dir():
            return []

        versions: list[int] = []
        for path in directory.iterdir():
            match = GOLDEN_FILE_PATTERN.match(path.name)
            assert match is not None, f"Unexpected golden file {path}"
            versions.append(int(match.group(1)))

        return sorted(versions)

    def read_golden_text(
        self,
        collection_name: DocumentCollectionName,
        version: int,
    ) -> str:
        return self.golden_path(collection_name, version).read_text(encoding="utf-8")

    def read_snapshot(
        self,
        document_type: type[PersistentDocument],
    ) -> StoredJsonObject | None:
        path: Path = self.snapshot_path(document_type)
        if not path.is_file():
            return None

        return parse_stored_object(path.read_text(encoding="utf-8"))


REPOSITORY_FILES: EvolutionFiles = EvolutionFiles()


def build_snapshot(
    document_type: type[PersistentDocument],
    collection_name: DocumentCollectionName,
    version: int,
) -> StoredJsonObject:
    return {
        "document_type": document_type.__name__,
        "collection": str(collection_name),
        "schema_version": version,
        "shape": stored_shape(document_type),
    }


def write_json(path: Path, content: JsonValue) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(content, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
