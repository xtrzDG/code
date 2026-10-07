"""Keep abc order."""

from base_typed_string import BaseTypedString


class StoredResponseBody(BaseTypedString):
    """
    The body of a stored answer to a creating request (UTF-8 JSON text),
    replayed byte for byte to a retry with the same idempotency key.
    """


# Keep abc order for all non example types, if possible.
