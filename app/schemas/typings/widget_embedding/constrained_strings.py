"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class WidgetLoaderIntegrity(BaseConstrainedTypedString):
    """
    Subresource Integrity hash of the loader (SHA-384, base64), the
    `integrity` attribute of the embed code.

    Example:
        integrity = WidgetLoaderIntegrity("sha384-" + "A" * 64)
    """

    min_length = 71
    max_length = 71
    pattern = r"^sha384-[A-Za-z0-9+/]{64}$"


class WidgetLoaderUrl(BaseConstrainedTypedString):
    """
    Address of the website chat's loader that embed codes point at: a
    versioned file under /widget/v/ that never changes once published.

    Example:
        loader_url = WidgetLoaderUrl(
            "https://api.example.com/widget/v/0f3a9c1e2b7d4a65.js"
        )
    """

    min_length = 30
    max_length = 2048
    pattern = r"^https?://[^\s/]+(/[^\s]*)?/widget/v/[0-9a-f]{16}\.js$"
