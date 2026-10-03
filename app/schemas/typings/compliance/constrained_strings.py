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


class DpaDocumentUrl(BaseConstrainedTypedString):
    """
    API path that serves the text of one agreement version (GET, JSON with
    Markdown; `?language=` picks the translation).

    Example:
        url = DpaDocumentUrl("/v1/legal/dpa/2026-10-01")
    """

    min_length = 2
    max_length = 200
    pattern = r"^/v1/legal/dpa/[0-9A-Za-z][0-9A-Za-z.\-_]*$"


# Keep abc order for all non example types, if possible.
