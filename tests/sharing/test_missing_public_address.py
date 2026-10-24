"""
A channel that answers but whose public address the platform never learned:
the Channels card says so (MISSING_PUBLIC_ADDRESS) by the same rule the share
links follow, and the share links skip it with the reason.
"""

import pytest

from app.schemas.constants.channels import ChannelKind, ChannelLinkState, ChannelStatus
from app.schemas.constants.sharing import ShareLinkGap, ShareLinkKind
from app.schemas.domain.channels import ChannelDocument, ChannelPublicProfile
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.sharing.constrained_strings import (
    InstagramUsername,
    WhatsAppNumberDigits,
)
from app.use_cases.channels.channel_views import build_channel_view
from app.utilities.sharing.share_links import (
    build_contact_links,
    build_share_links,
    find_link_state,
)

BUSINESS: BusinessId = BusinessId()


def channel(
    kind: ChannelKind,
    public: ChannelPublicProfile | None = None,
    status: ChannelStatus = ChannelStatus.CONNECTED,
    external_id: str | None = "1234567890",
) -> ChannelDocument:
    return ChannelDocument(
        business_id=BUSINESS,
        kind=kind,
        status=status,
        external_id=None if external_id is None else ChannelExternalId(external_id),
        public_profile=public,
    )


def test_whatsapp_without_its_number_is_flagged_and_skipped() -> None:
    whatsapp = channel(ChannelKind.WHATSAPP)

    assert find_link_state(whatsapp) is ChannelLinkState.MISSING_PUBLIC_ADDRESS
    assert build_channel_view(whatsapp).link_state is (
        ChannelLinkState.MISSING_PUBLIC_ADDRESS
    )
    [hosted, shared] = build_share_links([whatsapp], None, None, None)
    assert hosted.kind is ShareLinkKind.HOSTED_CHAT
    assert (shared.kind, shared.url, shared.gap) == (
        ShareLinkKind.WHATSAPP,
        None,
        ShareLinkGap.RECONNECT_CHANNEL,
    )
    assert build_contact_links([whatsapp], None) == []


@pytest.mark.parametrize(
    ("kind", "public", "url"),
    [
        (
            ChannelKind.WHATSAPP,
            ChannelPublicProfile(whatsapp_number=WhatsAppNumberDigits("995322111222")),
            "https://wa.me/995322111222",
        ),
        (
            ChannelKind.INSTAGRAM,
            ChannelPublicProfile(instagram_username=InstagramUsername("mtsvane.ezo")),
            "https://ig.me/m/mtsvane.ezo",
        ),
    ],
)
def test_a_known_address_is_linked_everywhere(
    kind: ChannelKind, public: ChannelPublicProfile, url: str
) -> None:
    connected = channel(kind, public)

    assert find_link_state(connected) is ChannelLinkState.LINKED
    assert build_channel_view(connected).link_state is ChannelLinkState.LINKED
    assert [str(link.url) for link in build_contact_links([connected], None)] == [url]


def test_instagram_without_its_username_is_flagged() -> None:
    assert find_link_state(channel(ChannelKind.INSTAGRAM)) is (
        ChannelLinkState.MISSING_PUBLIC_ADDRESS
    )


def test_channels_without_a_link_of_their_own_have_no_state() -> None:
    assert find_link_state(channel(ChannelKind.WEB_CHAT)) is None
    assert find_link_state(channel(ChannelKind.OWNER_TEST)) is None
    disconnected = channel(ChannelKind.WHATSAPP, status=ChannelStatus.DISABLED)
    assert find_link_state(disconnected) is None
    assert build_channel_view(disconnected).link_state is None
