"""Keep abc order.

(class) BaseConstrainedTypedString

Constrained transparent domain-typed string.

Design rules:

stores an exact runtime subtype
declares reusable value invariants on the type itself
supports min_length, max_length, and Python regular-expression constraints
validates direct construction without requiring Pydantic
preserves constraints and the exact subtype in Pydantic model fields
replaces field-level Annotated, StringConstraints, and AfterValidator composition
"""

from base_typed_string import BaseConstrainedTypedString


class ExampleConstrainedString(BaseConstrainedTypedString):
    """
    Constrained domain string example.

    Example:
        example_code = ExampleConstrainedString("example")

        assert isinstance(example_code, str)
        assert type(example_code) is ExampleConstrainedString
        assert type(example_code.upper()) is str
    """

    min_length = 3
    max_length = 20
    pattern = r"^[a-z]+$"


# Keep abc order for all non example types, if possible.
