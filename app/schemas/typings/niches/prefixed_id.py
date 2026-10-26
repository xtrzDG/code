"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class NicheTextReleaseId(BasePrefixedTypedId):
    """
    One published version of a niche's text overrides: derived (UUID v5)
    from the niche and the version number, so two admins publishing the
    same version at once store one of them.
    """

    prefix = "niche_text_release"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


# Keep abc order for all non example types, if possible.
