"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class SpendDay(BaseConstrainedTypedString):
    """
    One calendar day of spend, ISO `YYYY-MM-DD`: a business's own day in its
    time zone (its daily limits), or a UTC day (the platform's spend).

    Example:
        day = SpendDay("2026-10-05")
    """

    min_length = 10
    max_length = 10
    pattern = r"^\d{4}-\d{2}-\d{2}$"


class WidgetPageOrigin(BaseConstrainedTypedString):
    """
    The origin of the web page a website-chat request came from (its Origin
    header, else its Referer's), lowercased: scheme, host and a port only
    when it is not the scheme's default. "null" for a page without one (a
    sandboxed frame, a local file).

    Example:
        origin = WidgetPageOrigin("https://www.cafe-batumi.ge")
    """

    min_length = 4
    max_length = 300
    pattern = r"^(null|https?://[a-z0-9.\-]+(:[0-9]{1,5})?|https?://\[[0-9a-f:.]+\](:[0-9]{1,5})?)$"


class WidgetSiteAddress(BaseConstrainedTypedString):
    """
    A website an owner allows to show the business's chat, as they typed it
    ("cafe-batumi.ge", "https://www.cafe-batumi.ge/menu"); stored as its
    origin (`normalize_site_address`).
    """

    min_length = 1
    max_length = 300
