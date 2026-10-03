"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class WebsiteImportItemCount(BaseConstrainedTypedInt):
    """Number of knowledge drafts a website import has found so far."""

    ge = 0


class WebsitePageCount(BaseConstrainedTypedInt):
    """Number of pages of a website (planned, read or skipped by an import)."""

    ge = 0
    le = 100


# Keep abc order for all non example types, if possible.
