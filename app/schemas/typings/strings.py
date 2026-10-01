"""Keep abc order.

(class) BaseTypedString

Transparent domain-typed string.

Design rules:

stores an exact runtime subtype
behaves like plain str in normal string operations
normal string operations usually return plain str
preserves subtype in containers, pickle, and Pydantic model fields
does not introduce extra public domain-specific API
"""

from base_typed_string import BaseTypedString


class ExampleString(BaseTypedString):
    """
    Domain string example.

    Example:
        example_name = ExampleString("example")

        assert isinstance(example_name, str)
        assert type(example_name) is ExampleString
        assert type(example_name.upper()) is str
    """


# Keep abc order for all non example types, if possible.
