"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class WebLink(BaseConstrainedTypedString):
    """
    Absolute http(s) link from the business profile (menu, map, payment page).

    Example:
        menu = WebLink("https://example.com/menu.pdf")
    """

    min_length = 10
    max_length = 2048
    pattern = r"^https?://[^\s/]+(/[^\s]*)?$"


# Keep abc order for all non example types, if possible.
