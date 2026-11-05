"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class TeamMemberCount(BaseConstrainedTypedInt):
    """How many people the team of one business has (its members)."""

    ge = 0
    le = 100_000


# Keep abc order for all non example types, if possible.
