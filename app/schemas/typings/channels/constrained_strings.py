"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class PublicBaseUrl(BaseConstrainedTypedString):
    """
    Public HTTPS origin of this backend, used to register channel webhooks.

    Example:
        base_url = PublicBaseUrl("https://api.example.com")
    """

    min_length = 10
    max_length = 2048
    pattern = r"^https?://[^\s/]+(/[^\s]*)?$"


# Keep abc order for all non example types, if possible.
