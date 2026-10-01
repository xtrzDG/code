from collections.abc import Callable
from io import StringIO

from base_pydantic_schemas import (
    ArbitraryImmutableDTO,
    ArbitraryMutableDTO,
    ImmutableDTO,
    MutableDTO,
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


class ExampleMutableDTO(MutableDTO):
    """Mutable command/request DTO with strict typed fields."""

    count: ExampleInt
    deterministic_id: ExampleDeterministicId
    deterministic_prefixed_id: ExampleDeterministicPrefixedId
    is_enabled: ExampleBoolean
    name: ExampleString
    random_id: ExampleRandomId
    random_prefixed_id: ExampleRandomPrefixedId
    ratio: ExampleFloat


class ExampleImmutableDTO(ImmutableDTO):
    """Immutable read/result DTO returned as a stable snapshot."""

    count: ExampleInt
    deterministic_id: ExampleDeterministicId
    deterministic_prefixed_id: ExampleDeterministicPrefixedId
    is_enabled: ExampleBoolean
    name: ExampleString
    random_id: ExampleRandomId
    random_prefixed_id: ExampleRandomPrefixedId
    ratio: ExampleFloat


class ExampleArbitraryMutableDTO(ArbitraryMutableDTO):
    """Mutable runtime DTO that may carry arbitrary non-Pydantic objects."""

    mutable_input: ExampleMutableDTO
    output_buffer: StringIO
    publish_output: Callable[[ExampleImmutableDTO], None]


class ExampleArbitraryImmutableDTO(ArbitraryImmutableDTO):
    """Frozen runtime DTO that may carry arbitrary non-Pydantic objects."""

    immutable_output: ExampleImmutableDTO
    output_buffer: StringIO
    publish_output: Callable[[ExampleImmutableDTO], None]
