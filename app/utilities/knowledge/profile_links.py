"""The links of a business profile the assistant may send (send_link)."""

from app.schemas.constants.businesses import BusinessLinkKind
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.typings.businesses.constrained_strings import WebLink


def find_profile_link(
    profile: BusinessProfileDocument,
    kind: BusinessLinkKind,
) -> WebLink | None:
    """
    The profile's link of a kind; a map request falls back to the maps link
    of the address. None when there is none: no link is ever made up.
    """

    for link in profile.links:
        if link.kind is kind:
            return link.url

    if kind is BusinessLinkKind.MAP and profile.address is not None:
        return profile.address.maps_url

    return None
