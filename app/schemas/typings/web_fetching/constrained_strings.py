"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class WebCharsetName(BaseConstrainedTypedString):
    """
    Character set a web server named for a text it served (the `charset`
    of its Content-Type), e.g. "utf-8" or "windows-1251".

    Example:
        charset = WebCharsetName("utf-8")
    """

    min_length = 1
    max_length = 40
    pattern = r"^[A-Za-z0-9][A-Za-z0-9._:\-]*$"


class WebMediaType(BaseConstrainedTypedString):
    """
    Media type of a resource on the web, lower case without parameters,
    e.g. "text/html" or "application/pdf".

    Example:
        media_type = WebMediaType("text/html")
    """

    min_length = 3
    max_length = 100
    pattern = r"^[a-z0-9][a-z0-9!#$&^_.+\-]*/[a-z0-9][a-z0-9!#$&^_.+\-]*$"


class WebResourceUrl(BaseConstrainedTypedString):
    """
    Absolute http(s) address of a resource on the web that the platform
    reads itself (a page of a business's website, a menu behind a link).
    Whether it may be fetched is decided by the safe fetcher, not here.

    Example:
        url = WebResourceUrl("https://cafe.example/menu")
    """

    min_length = 10
    max_length = 2048
    pattern = r"^https?://[^\s/?#]+([/?#][^\s]*)?$"


# Keep abc order for all non example types, if possible.
