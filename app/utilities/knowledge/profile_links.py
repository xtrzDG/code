"""The links of a business profile the assistant may send (send_link)."""

from collections.abc import Sequence

from app.schemas.constants.businesses import BusinessLinkKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import BusinessLink, BusinessProfileDocument
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.utilities.sharing.share_links import choose_privacy_url


def read_profile_links(profile: BusinessProfileDocument) -> list[BusinessLink]:
    """
    Every link of the profile as the cabinet and the assistant see them:
    the stored links and, last, the privacy notice and the Google review
    page (each stored on its own).
    """

    links: list[BusinessLink] = [link.model_copy() for link in profile.links]
    if profile.privacy_notice_url is not None:
        links.append(
            BusinessLink(kind=BusinessLinkKind.PRIVACY, url=profile.privacy_notice_url)
        )

    if profile.google_review_url is not None:
        links.append(
            BusinessLink(
                kind=BusinessLinkKind.GOOGLE_REVIEW, url=profile.google_review_url
            )
        )

    return links


def store_profile_links(
    profile: BusinessProfileDocument,
    links: Sequence[BusinessLink],
) -> None:
    """
    Keep checked links on the profile: the privacy notice and the Google
    review page in their own fields, every other kind in `links` (see
    `BusinessProfileDocument`).
    """

    privacy_url: WebLink | None = None
    review_url: WebLink | None = None
    stored: list[BusinessLink] = []
    for link in links:
        if link.kind is BusinessLinkKind.PRIVACY:
            privacy_url = link.url
        elif link.kind is BusinessLinkKind.GOOGLE_REVIEW:
            review_url = link.url
        else:
            stored.append(link.model_copy())

    profile.links = stored
    profile.privacy_notice_url = privacy_url
    profile.google_review_url = review_url


def find_profile_link(
    profile: BusinessProfileDocument,
    kind: BusinessLinkKind,
) -> WebLink | None:
    """
    The profile's link of a kind; a map request falls back to the maps link
    of the address. None when there is none: no link is ever made up.
    """

    for link in read_profile_links(profile):
        if link.kind is kind:
            return link.url

    if kind is BusinessLinkKind.MAP and profile.address is not None:
        return profile.address.maps_url

    return None


def find_sendable_link(
    business: BusinessDocument,
    profile: BusinessProfileDocument | None,
    kind: BusinessLinkKind,
    cabinet_base_url: CabinetBaseUrl | None,
) -> WebLink | None:
    """
    The link send_link sends: the profile's link of the kind (`find_profile_link`),
    and for the privacy notice, without one of the business's own, the
    platform's hosted notice of its chat page (`/c/{slug}/privacy`), so the
    link a call's greeting offers can always be sent (VOICE-05; None only
    while CABINET_BASE_URL is not set).
    """

    if kind is BusinessLinkKind.PRIVACY:
        return choose_privacy_url(business, profile, cabinet_base_url)

    return None if profile is None else find_profile_link(profile, kind)
