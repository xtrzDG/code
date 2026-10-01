"""Keep abc order.

(class) BaseConstrainedTypedFloat

Constrained transparent domain-typed finite float.

Design rules:

stores an exact runtime subtype
accepts only exact built-in finite float input
declares reusable value invariants on the type itself
supports gt, ge, lt, and le constraints
validates direct construction without requiring Pydantic
preserves constraints and the exact subtype in Pydantic model fields
does not provide ambiguous floating-point multiple_of semantics
"""

from base_typed_float import BaseConstrainedTypedFloat


class ExampleConstrainedFloat(BaseConstrainedTypedFloat):
    """
    Constrained domain finite-float example.

    Example:
        example_ratio = ExampleConstrainedFloat(0.75)

        assert isinstance(example_ratio, float)
        assert type(example_ratio) is ExampleConstrainedFloat
        assert type(example_ratio + 0.05) is float
    """

    ge = 0.0
    le = 1.0


# Keep abc order for all non example types, if possible.
