"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class ExtractedPriceAmount(BaseConstrainedTypedString):
    """
    Price as printed on a menu, normalized to a plain decimal in major units.

    Example:
        price = ExtractedPriceAmount("18.50")
    """

    min_length = 1
    max_length = 20
    pattern = r"^[0-9]{1,12}(\.[0-9]{1,4})?$"


class MenuSourceBase64(BaseConstrainedTypedString):
    """
    Uploaded menu file (photo, PDF or text) encoded as standard base64: a
    file of at most 15 MB (4 characters per 3 bytes).

    Example:
        data = MenuSourceBase64("JVBERi0xLjQK")
    """

    max_length = 20 * 1024 * 1024


class MenuSourceMediaType(BaseConstrainedTypedString):
    """
    Media type of an uploaded menu, e.g. "image/jpeg" or "application/pdf".

    Example:
        media_type = MenuSourceMediaType("application/pdf")
    """

    min_length = 3
    max_length = 100
    pattern = r"^[a-z]+/[a-z0-9.+\-]+$"


# Keep abc order for all non example types, if possible.
