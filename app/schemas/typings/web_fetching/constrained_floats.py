"""Keep abc order."""

from base_typed_float import BaseConstrainedTypedFloat


class WebFetchTimeoutSeconds(BaseConstrainedTypedFloat):
    """
    The whole time one fetch may take, redirects and reading included
    (not per network operation), in seconds.
    """

    gt = 0.0
    le = 60.0


# Keep abc order for all non example types, if possible.
