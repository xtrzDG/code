"""Keep abc order.

(class) BaseTypedFloat

Transparent domain-typed finite float.

Design rules:

stores an exact runtime subtype
accepts only exact built-in finite float input
behaves like plain float in normal numeric operations
normal numeric operations usually return plain float
preserves subtype in containers, pickle, and Pydantic model fields
does not introduce extra public domain-specific API
"""

from base_typed_float import BaseTypedFloat


class ExampleFloat(BaseTypedFloat):
    """
    Domain finite-float example.

    Example:
        example_ratio = ExampleFloat(0.75)

        assert isinstance(example_ratio, float)
        assert type(example_ratio) is ExampleFloat
        assert type(example_ratio + 0.05) is float
    """


# Keep abc order for all non example types, if possible.
