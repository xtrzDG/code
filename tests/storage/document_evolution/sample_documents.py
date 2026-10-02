"""
A maximal sample of a stored document type for its golden fixture: every
optional field set, every list with one element, every nested object in
full, ids derived from the field path (stable across runs), and validated
strictly by the current code.
"""

import hashlib
import json
import types
import typing
import uuid
from enum import Enum

from base_pydantic_schemas import PersistentDocument
from base_typed_float import BaseConstrainedTypedFloat, BaseTypedFloat
from base_typed_id import BasePrefixedTypedId
from base_typed_int import BaseConstrainedTypedInt, BaseTypedInt
from base_typed_string import BaseConstrainedTypedString, BaseTypedString
from pydantic import BaseModel
from typed_time_provider import BaseTimeUnit

from app.adapters.storage.document_upgrades import (
    SCHEMA_VERSION_FIELD_NAME,
    declared_schema_version,
    schema_version_text,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from tests.storage.document_evolution.sample_values import (
    CONSTRAINED_TEXT_SAMPLES,
    INTEGER_SAMPLES,
    PLAIN_TEXT_SAMPLES,
    SAMPLE_MICROSECONDS,
)

type JsonValue = object
UNSTRUCTURED_TEXT_PATTERNS: frozenset[str | None] = frozenset({None, r"\S"})
UNCONSTRAINED_INTEGER_SAMPLE: int = 7
UNCONSTRAINED_FLOAT_SAMPLE: float = 0.5


def sample_document[StoredDocument: PersistentDocument](
    document_type: type[StoredDocument],
    collection_name: DocumentCollectionName,
) -> StoredDocument:
    raw: dict[str, JsonValue] = sample_object(document_type, str(collection_name))
    version = declared_schema_version(document_type)
    if version is not None:
        raw[SCHEMA_VERSION_FIELD_NAME] = str(schema_version_text(version))

    return document_type.model_validate_json(json.dumps(raw))


def sample_object(model: type[BaseModel], path: str) -> dict[str, JsonValue]:
    return {
        name: sample_value(field.annotation, f"{path}.{name}")
        for name, field in model.model_fields.items()
    }


def sample_value(annotation: object, path: str) -> JsonValue:
    origin = typing.get_origin(annotation)
    arguments: tuple[object, ...] = typing.get_args(annotation)
    if origin is typing.Annotated:
        return sample_value(arguments[0], path)

    if origin in (typing.Union, types.UnionType):
        present: list[object] = [item for item in arguments if item is not type(None)]
        return sample_value(present[0], path)

    if origin in (list, set, frozenset, tuple):
        return [sample_value(arguments[0], f"{path}[]")]

    if origin is dict:
        return {str(sample_value(arguments[0], path)): sample_value(arguments[1], path)}

    if origin is typing.Literal:
        return arguments[0]

    if isinstance(annotation, type):
        return sample_of_type(annotation, path)

    raise TypeError(f"No sample for {annotation!r} at {path}.")


def sample_of_type(annotation: type, path: str) -> JsonValue:
    if issubclass(annotation, BaseModel):
        return sample_object(annotation, path)

    if issubclass(annotation, Enum):
        return next(iter(annotation)).value

    if annotation is bool:
        return True

    if issubclass(annotation, BasePrefixedTypedId):
        return str(annotation(stable_uuid(path, annotation.uuid_version or 4)))

    if issubclass(annotation, BaseConstrainedTypedString):
        return constrained_text(annotation)

    if issubclass(annotation, BaseTypedString):
        name: str = annotation.__name__
        return PLAIN_TEXT_SAMPLES.get(name, f"Sample {name}")

    if issubclass(annotation, BaseTimeUnit):
        return SAMPLE_MICROSECONDS

    if issubclass(annotation, BaseConstrainedTypedInt):
        return constrained_integer(annotation)

    if issubclass(annotation, BaseTypedInt):
        return UNCONSTRAINED_INTEGER_SAMPLE

    if issubclass(annotation, BaseConstrainedTypedFloat):
        return constrained_float(annotation)

    if issubclass(annotation, BaseTypedFloat):
        return UNCONSTRAINED_FLOAT_SAMPLE

    raise TypeError(f"No sample for {annotation.__name__} at {path}.")


def stable_uuid(path: str, version: int) -> uuid.UUID:
    """
    A UUID of the id's version (v4 when it takes any) derived from the field
    path: the same golden on every run.
    """

    return uuid.UUID(
        bytes=hashlib.sha256(path.encode()).digest()[:16], version=version
    )


def constrained_text(annotation: type[BaseConstrainedTypedString]) -> str:
    if annotation.__name__ in CONSTRAINED_TEXT_SAMPLES:
        return CONSTRAINED_TEXT_SAMPLES[annotation.__name__]

    pattern: object = getattr(annotation, "pattern", None)
    if pattern not in UNSTRUCTURED_TEXT_PATTERNS:
        raise KeyError(
            f"Add a sample of {annotation.__name__} (pattern {pattern!r}) to "
            "tests/storage/document_evolution/sample_values.py."
        )

    maximum: object = getattr(annotation, "max_length", None)
    text: str = f"Sample {annotation.__name__}"
    return text if not isinstance(maximum, int) else text[:maximum]


def constrained_integer(annotation: type[BaseConstrainedTypedInt]) -> int:
    if annotation.__name__ in INTEGER_SAMPLES:
        return INTEGER_SAMPLES[annotation.__name__]

    lowest: int = 1
    for name, offset in (("ge", 0), ("gt", 1)):
        bound: object = getattr(annotation, name, None)
        if isinstance(bound, int):
            lowest = max(lowest, bound + offset)

    return lowest


def constrained_float(annotation: type[BaseConstrainedTypedFloat]) -> float:
    low: object = getattr(annotation, "ge", None)
    high: object = getattr(annotation, "le", None)
    if isinstance(low, float) and isinstance(high, float):
        return (low + high) / 2

    return 0.5
