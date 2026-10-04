"""Links that open a conversation in each channel, and the share list."""

from app.schemas.constants.businesses import BusinessLinkKind
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.sharing import ShareLinkGap, ShareLinkKind
from app.schemas.domain.channels import ChannelDocument, ChannelPublicProfile
from app.schemas.domain.profiles import (
    BusinessContacts,
    BusinessLink,
    BusinessProfileDocument,
)
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import (
    MetaObjectId,
    TelegramBotUsername,
)
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.schemas.typings.sharing.constrained_strings import (
    InstagramUsername,
    MetaPageUsername,
    ShareSourceTag,
    WhatsAppNumberDigits,
)
from app.utilities.channels.channel_links import (
    build_hosted_chat_url,
    build_instagram_link,
    build_messenger_link,
    build_phone_link,
    build_telegram_link,
    build_whatsapp_link,
)
from app.utilities.knowledge.profile_links import (
    find_profile_link,
    read_profile_links,
    store_profile_links,
)
from app.utilities.sharing.share_links import build_contact_links, build_share_links

BUSINESS = BusinessId("business_0b6c2f5e-1d1a-4c55-9a3e-2f1d5b7c9e01")
QR = ShareSourceTag("qr")


def channel(
    kind: ChannelKind,
    external_id: str | None = None,
    profile: ChannelPublicProfile | None = None,
    status: ChannelStatus = ChannelStatus.CONNECTED,
) -> ChannelDocument:
    return ChannelDocument(
        business_id=BUSINESS,
        kind=kind,
        external_id=None if external_id is None else ChannelExternalId(external_id),
        status=status,
        public_profile=profile,
    )


def profile(public_phone: str | None = None) -> BusinessProfileDocument:
    return BusinessProfileDocument(
        business_id=BUSINESS,
        niche_key=NicheKey.RESTAURANT,
        answers_language=LanguageTag("en"),
        contacts=BusinessContacts(
            public_phone_number=(
                None if public_phone is None else E164PhoneNumber(public_phone)
            )
        ),
    )


class TestLinkBuilders:
    def test_hosted_page_carries_the_source_tag(self) -> None:
        base = CabinetBaseUrl("https://app.example.com/")

        assert build_hosted_chat_url(base, "cafe-batumi") == (
            "https://app.example.com/c/cafe-batumi"
        )
        assert build_hosted_chat_url(base, "cafe-batumi", QR) == (
            "https://app.example.com/c/cafe-batumi?src=qr"
        )

    def test_messenger_links_carry_the_tag_as_a_ref(self) -> None:
        assert build_messenger_link(MetaPageUsername("cafebatumi"), QR) == (
            "https://m.me/cafebatumi?ref=qr"
        )
        assert build_messenger_link(MetaObjectId("1234567890")) == (
            "https://m.me/1234567890"
        )
        assert build_instagram_link(InstagramUsername("cafe.batumi"), QR) == (
            "https://ig.me/m/cafe.batumi?ref=qr"
        )

    def test_whatsapp_and_telegram_links_carry_the_tag_their_own_way(self) -> None:
        assert build_whatsapp_link(WhatsAppNumberDigits("995555123456")) == (
            "https://wa.me/995555123456"
        )
        # The customer sends the greeting with the code; the adapter reads it.
        assert build_whatsapp_link(
            WhatsAppNumberDigits("995555123456"), QR, "Здравствуйте!"
        ) == (
            "https://wa.me/995555123456?text="
            "%D0%97%D0%B4%D1%80%D0%B0%D0%B2%D1%81%D1%82%D0%B2%D1%83%D0%B9%D1%82%D0%B5"
            "%21%20%28%23qr%29"
        )
        assert build_telegram_link(TelegramBotUsername("cafe_batumi_bot")) == (
            "https://t.me/cafe_batumi_bot"
        )
        assert build_telegram_link(TelegramBotUsername("cafe_batumi_bot"), QR) == (
            "https://t.me/cafe_batumi_bot?start=src_qr"
        )

    def test_phone_links_stay_untagged(self) -> None:
        assert build_phone_link(E164PhoneNumber("+995555123456")) == (
            "tel:+995555123456"
        )


class TestShareLinks:
    def test_hosted_page_first_then_connected_channels_in_order(self) -> None:
        channels = [
            channel(
                ChannelKind.WHATSAPP,
                "106540352242922",
                ChannelPublicProfile(
                    whatsapp_number=WhatsAppNumberDigits("995555123456")
                ),
            ),
            channel(ChannelKind.TELEGRAM, "cafe_batumi_bot"),
            channel(
                ChannelKind.INSTAGRAM,
                "17841400000000001",
                ChannelPublicProfile(
                    instagram_username=InstagramUsername("cafe.batumi")
                ),
            ),
            channel(ChannelKind.MESSENGER, "1234567890", status=ChannelStatus.DISABLED),
            channel(ChannelKind.PHONE, "+995322000111"),
            channel(ChannelKind.WEB_CHAT),
        ]
        hosted = build_hosted_chat_url(
            CabinetBaseUrl("https://app.example.com"), "cafe-batumi", QR
        )

        links = build_share_links(
            channels, profile("+995322123456"), hosted, QR, LanguageTag("ka")
        )

        assert [(link.kind, link.url, link.label) for link in links] == [
            (
                ShareLinkKind.HOSTED_CHAT,
                "https://app.example.com/c/cafe-batumi?src=qr",
                "app.example.com/c/cafe-batumi?src=qr",
            ),
            (
                ShareLinkKind.TELEGRAM,
                "https://t.me/cafe_batumi_bot?start=src_qr",
                "@cafe_batumi_bot",
            ),
            (
                ShareLinkKind.INSTAGRAM,
                "https://ig.me/m/cafe.batumi?ref=qr",
                "@cafe.batumi",
            ),
            (
                ShareLinkKind.WHATSAPP,
                # "გამარჯობა! (#qr)", the greeting language's greeting.
                "https://wa.me/995555123456?text="
                "%E1%83%92%E1%83%90%E1%83%9B%E1%83%90%E1%83%A0%E1%83%AF%E1%83%9D"
                "%E1%83%91%E1%83%90%21%20%28%23qr%29",
                "+995555123456",
            ),
            # The public number forwards unanswered calls to the assistant.
            (ShareLinkKind.PHONE, "tel:+995322123456", "+995322123456"),
        ]

    def test_channels_without_a_known_address_ask_for_a_reconnect(self) -> None:
        channels = [
            channel(ChannelKind.WHATSAPP, "106540352242922"),
            channel(ChannelKind.INSTAGRAM, "17841400000000001"),
            channel(ChannelKind.MESSENGER, "1234567890"),
        ]

        links = build_share_links(channels, None, None, None)

        assert [(link.kind, link.url, link.gap) for link in links] == [
            (ShareLinkKind.HOSTED_CHAT, None, ShareLinkGap.NOT_CONFIGURED),
            (ShareLinkKind.INSTAGRAM, None, ShareLinkGap.RECONNECT_CHANNEL),
            # A page id opens Messenger too.
            (ShareLinkKind.MESSENGER, "https://m.me/1234567890", None),
            (ShareLinkKind.WHATSAPP, None, ShareLinkGap.RECONNECT_CHANNEL),
        ]

    def test_the_assistant_line_is_called_without_a_public_number(self) -> None:
        links = build_share_links(
            [channel(ChannelKind.PHONE, "+995322000111")], profile(), None, None
        )

        assert links[-1].url == "tel:+995322000111"

    def test_contact_links_leave_out_the_hosted_page_and_the_gaps(self) -> None:
        channels = [
            channel(ChannelKind.TELEGRAM, "cafe_batumi_bot"),
            channel(ChannelKind.WHATSAPP, "106540352242922"),
        ]

        contacts = build_contact_links(channels, None)

        assert [(link.kind, link.url) for link in contacts] == [
            (ShareLinkKind.TELEGRAM, "https://t.me/cafe_batumi_bot")
        ]


class TestPrivacyLink:
    def test_the_privacy_notice_is_kept_apart_and_read_back_last(self) -> None:
        stored = profile()
        store_profile_links(
            stored,
            [
                BusinessLink(
                    kind=BusinessLinkKind.PRIVACY,
                    url=WebLink("https://cafe.example/privacy"),
                ),
                BusinessLink(
                    kind=BusinessLinkKind.MENU, url=WebLink("https://cafe.example/menu")
                ),
            ],
        )

        assert [link.kind for link in stored.links] == [BusinessLinkKind.MENU]
        assert stored.privacy_notice_url == "https://cafe.example/privacy"
        assert [link.kind for link in read_profile_links(stored)] == [
            BusinessLinkKind.MENU,
            BusinessLinkKind.PRIVACY,
        ]
        assert find_profile_link(stored, BusinessLinkKind.PRIVACY) == (
            "https://cafe.example/privacy"
        )

    def test_saving_links_without_it_removes_the_privacy_notice(self) -> None:
        stored = profile()
        stored.privacy_notice_url = WebLink("https://cafe.example/privacy")

        store_profile_links(stored, [])

        assert stored.privacy_notice_url is None
        assert find_profile_link(stored, BusinessLinkKind.PRIVACY) is None
