"""Keep abc order.

(class) BaseTypedInt

Transparent domain-typed integer.

Design rules:

stores an exact runtime subtype
behaves like plain int in normal numeric operations
normal numeric operations usually return plain int
preserves subtype in containers, pickle, and Pydantic model fields
does not introduce extra public domain-specific API
accepts only real int input and rejects bool explicitly
"""

from base_typed_int import BaseTypedInt


class ExampleInt(BaseTypedInt):
    """
    Domain integer example.

    Example:
        example_count = ExampleInt(42)

        assert isinstance(example_count, int)
        assert type(example_count) is ExampleInt
        assert type(example_count + 1) is int
    """


# Keep abc order for all non example types, if possible.
