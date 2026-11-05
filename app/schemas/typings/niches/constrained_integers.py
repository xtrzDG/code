"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class NicheOverrideCount(BaseConstrainedTypedInt):
    """How many texts (field and language) a niche's override set replaces."""

    ge = 0


class NicheTextLengthLimit(BaseConstrainedTypedInt):
    """
    The longest wording an admin may give one field of a niche template:
    what the profile or the knowledge base accepts for it (a handoff rule
    300 characters, a tone 200).
    """

    ge = 1
    le = 1000


class NicheTextVersion(BaseConstrainedTypedInt):
    """
    A published version of a niche's text overrides, counted from 1 per
    niche; 0 names the code template itself (no overrides), which a revert
    may return to.
    """

    ge = 0


# Keep abc order for all non example types, if possible.
