"""Keep abc order.

(class) BaseConstrainedTypedInt

Constrained transparent domain-typed integer.

Design rules:

stores an exact runtime subtype
declares reusable value invariants on the type itself
supports gt, ge, lt, le, and multiple_of constraints
validates direct construction without requiring Pydantic
preserves constraints and the exact subtype in Pydantic model fields
replaces field-level Annotated and AfterValidator constraint composition
"""

from base_typed_int import BaseConstrainedTypedInt


class ExampleConstrainedInt(BaseConstrainedTypedInt):
    """
    Constrained domain integer example.

    Example:
        example_percentage = ExampleConstrainedInt(50)

        assert isinstance(example_percentage, int)
        assert type(example_percentage) is ExampleConstrainedInt
        assert type(example_percentage + 1) is int
    """

    ge = 0
    le = 100
    multiple_of = 5


# Keep abc order for all non example types, if possible.
