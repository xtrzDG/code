from base_pydantic_schemas import (
    BaseDocument,
    PersistentDocument,
    UnixMicrosecondTimestampedMixin,
    UnixMillisecondTimestampedMixin,
    UnixNanosecondTimestampedMixin,
    VersionedMixin,
)

from app.schemas.typings.booleans import ExampleBoolean
from app.schemas.typings.floats import ExampleFloat
from app.schemas.typings.ids import ExampleDeterministicId, ExampleRandomId
from app.schemas.typings.integers import ExampleInt
from app.schemas.typings.prefixed_id import (
    ExampleDeterministicPrefixedId,
    ExampleRandomPrefixedId,
)
from app.schemas.typings.strings import ExampleString


class ExampleDocument(BaseDocument):
    """Default persisted document with microsecond timestamps and schema_version."""

    count: ExampleInt
    deterministic_id: ExampleDeterministicId
    deterministic_prefixed_id: ExampleDeterministicPrefixedId
    is_enabled: ExampleBoolean
    name: ExampleString
    random_id: ExampleRandomId
    random_prefixed_id: ExampleRandomPrefixedId
    ratio: ExampleFloat


class ExamplePersistentDocument(PersistentDocument):
    """Persistence-neutral document with only explicitly declared fields."""

    count: ExampleInt
    name: ExampleString
    random_id: ExampleRandomId


class ExampleMicrosecondTimestampedDocument(
    UnixMicrosecondTimestampedMixin,
    VersionedMixin,
    PersistentDocument,
):
    """Custom persisted document with microsecond timestamps."""

    count: ExampleInt
    name: ExampleString
    random_id: ExampleRandomId


class ExampleMillisecondTimestampedDocument(
    UnixMillisecondTimestampedMixin,
    VersionedMixin,
    PersistentDocument,
):
    """Custom persisted document with millisecond timestamps."""

    count: ExampleInt
    name: ExampleString
    random_id: ExampleRandomId


class ExampleNanosecondTimestampedDocument(
    UnixNanosecondTimestampedMixin,
    VersionedMixin,
    PersistentDocument,
):
    """Custom persisted document with nanosecond timestamps."""

    count: ExampleInt
    name: ExampleString
    random_id: ExampleRandomId
