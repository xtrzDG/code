"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class DpaDocumentVersion(BaseConstrainedTypedString):
    """
    Version of the data processing agreement text, e.g. "2026-10-01".

    Example:
        version = DpaDocumentVersion("2026-10-01")
    """

    min_length = 1
    max_length = 32
    pattern = r"^[0-9A-Za-z][0-9A-Za-z.\-_]*$"


# Keep abc order for all non example types, if possible.
