"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class CommentTriggerKeywordCount(BaseConstrainedTypedInt):
    """
    How many keywords an Instagram account's comment replies listen for (at
    most 20: a short list the owner can read at a glance).

    Example:
        count = CommentTriggerKeywordCount(3)
    """

    ge = 0
    le = 20


class MetaPageCount(BaseConstrainedTypedInt):
    """How many Facebook pages a sign-in offered to pick from."""

    ge = 0
    le = 1000


# Keep abc order for all non example types, if possible.
