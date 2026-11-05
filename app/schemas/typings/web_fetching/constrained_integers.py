"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class WebFetchByteLimit(BaseConstrainedTypedInt):
    """
    The most bytes the safe fetcher reads of one response body (after
    decompression); a larger body is refused, never cut.
    """

    ge = 1
    le = 20 * 1024 * 1024


# Keep abc order for all non example types, if possible.
