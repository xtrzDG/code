"""(class) BaseTypedId

Transparent domain-typed identifier based on UUID.

Design rules:

stores an exact runtime subtype
serializes as plain str
preserves subtype in containers, pickle, and Pydantic model fields
uses native pydantic-core uuid schema for OpenAPI format "uuid"
defaults to UUID v4 and auto-generates on None
"""

from typing import ClassVar, Literal

from base_typed_id import BaseTypedId


class ExampleDeterministicId(BaseTypedId):
    """
    Deterministic UUID v5 identifier.

    Example:
        from base_typed_id import deterministically_from_words

        example_id = deterministically_from_words(
            ExampleDeterministicId,
            words=[
                "source:example",
                "record:42",
            ],
        )

    Calling ExampleDeterministicId() without an explicit value is intentionally
    rejected because uuid_version is 5.
    """

    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


class ExampleRandomId(BaseTypedId):
    """
    Random UUID v4 identifier.

    Example:
        generated_id = ExampleRandomId()
        restored_id = ExampleRandomId(str(generated_id))

        assert type(generated_id) is ExampleRandomId
        assert type(restored_id) is ExampleRandomId
    """


# Keep abc order for all non example types, if possible.
