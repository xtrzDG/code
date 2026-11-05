"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class MenuLineCount(BaseConstrainedTypedInt):
    """Number of menu lines in an import (for example lines that were skipped)."""

    ge = 0


# Keep abc order for all non example types, if possible.
