"""Keep abc order.

(class) BasePrefixedTypedId

Transparent domain-typed identifier with a class-level canonical prefix.

Canonical runtime form: "<prefix>_<uuid>"

Rules:

prefix is a class-level invariant
prefix must be canonical lowercase snake case
regex is class-level and derived from prefix
stores exact runtime subtype
serializes as plain str
"""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class ExampleDeterministicPrefixedId(BasePrefixedTypedId):
    """
    Deterministic prefixed UUID v5 identifier.

    Example:
        from uuid import NAMESPACE_URL, uuid5

        example_id = ExampleDeterministicPrefixedId(
            uuid5(NAMESPACE_URL, "source:example/record:42"),
        )

        assert str(example_id).startswith("example_")

    Create values from an explicit UUID v5 value. The package-level
    deterministically_from_words factory currently supports BaseTypedId
    subclasses, not BasePrefixedTypedId subclasses.
    """

    prefix = "example"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


class ExampleRandomPrefixedId(BasePrefixedTypedId):
    """
    Random prefixed UUID v4 identifier.

    Example:
        generated_id = ExampleRandomPrefixedId()
        restored_id = ExampleRandomPrefixedId(str(generated_id))

        assert str(generated_id).startswith("example_")
        assert type(restored_id) is ExampleRandomPrefixedId
    """

    prefix = "example"


# Keep abc order for all non example types, if possible.
