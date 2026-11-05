"""Keep abc order."""

from base_typed_string import BaseTypedString


class WebsitePageText(BaseTypedString):
    """
    The visible text of a page of a business's website, as the sanitizer
    left it: no scripts, styles or hidden elements, one block per line.
    Untrusted: it is data for the reader model, never instructions.
    """


class WebsitePageTitle(BaseTypedString):
    """The title of a page of a business's website (its <title>)."""


# Keep abc order for all non example types, if possible.
