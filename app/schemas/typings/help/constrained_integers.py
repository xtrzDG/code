"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class HelpArticleOrder(BaseConstrainedTypedInt):
    """
    Where a help article stands among the articles of its topic in the
    help center (smaller first).
    """

    ge = 0
    le = 999


# Keep abc order for all non example types, if possible.
