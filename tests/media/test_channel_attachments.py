"""
Every channel reads the attachments of its webhook messages: the payloads
are shaped like each platform's documented samples (fixtures/).
"""

from typing import Any

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.media import AttachmentKind
from app.schemas.dto.channels.channel_webhooks import ChannelInboundMessage
from tests.channels.testbed import ChannelsTestbed
from tests.media.recorded_payloads import as_payload, load_fixture


def kinds(message: ChannelInboundMessage) -> list[AttachmentKind]:
    return [attachment.kind for attachment in message.attachments]


class TestWhatsApp:
    def parse(self) -> list[ChannelInboundMessage]:
        return ChannelsTestbed().whatsapp_adapter.parse_webhook(
            as_payload(load_fixture("whatsapp_media_webhook.json"))
        )

    def test_every_message_but_the_reaction_is_read(self) -> None:
        messages = self.parse()

        assert [str(m.provider_message_id) for m in messages] == [
            "wamid.voice-0001",
            "wamid.image-0002",
            "wamid.location-0003",
            "wamid.sticker-0004",
            "wamid.contacts-0005",
            "wamid.video-0006",
            "wamid.document-0007",
            "wamid.unsupported-0008",
        ]
        assert [kinds(m) for m in messages] == [
            [AttachmentKind.AUDIO],
            [AttachmentKind.IMAGE],
            [AttachmentKind.LOCATION],
            [AttachmentKind.STICKER],
            [AttachmentKind.CONTACT],
            [AttachmentKind.OTHER],
            [AttachmentKind.OTHER],
            [AttachmentKind.OTHER],
        ]
        assert all(m.channel is ChannelKind.WHATSAPP for m in messages)
        assert all(m.contact_name == "Nino Beridze" for m in messages)
        assert all(m.contact_phone_number == "+995599123456" for m in messages)

    def test_voice_note_and_photo_keep_the_media_id_type_and_caption(self) -> None:
        voice, photo, *_ = self.parse()

        [audio] = voice.attachments
        assert audio.provider_media_id == "1003383421387256"
        assert audio.mime_type == "audio/ogg; codecs=opus"
        assert audio.caption is None
        assert voice.text == ""

        [image] = photo.attachments
        assert image.provider_media_id == "1479537139650973"
        assert image.mime_type == "image/jpeg"
        assert image.caption == "Is this dish on your menu?"

    def test_a_place_and_the_captions_of_files_it_does_not_read(self) -> None:
        messages = self.parse()
        [place] = messages[2].attachments
        assert place.location is not None
        assert float(place.location.latitude) == 41.6912
        assert float(place.location.longitude) == 44.8073
        assert place.location.name == "Old Town"
        assert place.location.address == "Kote Abkhazi St 27, Tbilisi"

        assert messages[5].attachments[0].caption == "The hall last night"
        assert messages[6].attachments[0].caption == "Our group list"
        # A file the assistant does not read is not downloaded.
        assert messages[5].attachments[0].provider_media_id is None


class TestTelegram:
    def parse_all(self) -> list[ChannelInboundMessage]:
        adapter = ChannelsTestbed().telegram_adapter
        messages: list[ChannelInboundMessage] = []
        for update in load_fixture("telegram_media_updates.json"):
            messages.extend(adapter.parse_webhook(as_payload(update)))
        return messages

    def test_every_update_gives_one_message_with_its_attachment(self) -> None:
        messages = self.parse_all()

        assert [kinds(m) for m in messages] == [
            [AttachmentKind.AUDIO],
            [AttachmentKind.IMAGE],
            [AttachmentKind.LOCATION],
            [AttachmentKind.LOCATION],
            [AttachmentKind.STICKER],
            [AttachmentKind.IMAGE],
            [AttachmentKind.CONTACT],
            [AttachmentKind.OTHER],
            [AttachmentKind.AUDIO],
        ]
        assert [str(m.provider_message_id) for m in messages][:2] == [
            "555000111:101",
            "555000111:102",
        ]

    def test_voice_note_tells_its_length_and_size(self) -> None:
        [voice] = self.parse_all()[0].attachments

        assert voice.provider_media_id == "voice-file-0001"
        assert voice.mime_type == "audio/ogg"
        assert voice.duration_seconds == 7
        assert voice.declared_bytes == 21480

    def test_the_largest_photo_size_and_its_caption(self) -> None:
        photo_message = self.parse_all()[1]
        [photo] = photo_message.attachments

        assert photo.provider_media_id == "photo-file-large"
        assert photo.declared_bytes == 118230
        assert photo.caption == "Это блюдо есть в меню?"
        assert photo_message.text == ""

    def test_places_venues_pictures_sent_as_files_and_audio_files(self) -> None:
        messages = self.parse_all()

        pin = messages[2].attachments[0].location
        assert pin is not None
        assert pin.name is None
        venue = messages[3].attachments[0].location
        assert venue is not None
        assert (venue.name, venue.address) == ("Mtsvane Ezo", "Kote Abkhazi St 27")

        picture = messages[5].attachments[0]
        assert picture.provider_media_id == "document-photo-0001"
        assert picture.caption == "Вот фото"

        audio_file = messages[8].attachments[0]
        assert audio_file.mime_type == "audio/mpeg"
        assert audio_file.duration_seconds == 31


class TestMetaPages:
    def parse(self, adapter_name: str, fixture: str) -> list[ChannelInboundMessage]:
        adapter = getattr(ChannelsTestbed(), adapter_name)
        messages: list[ChannelInboundMessage] = adapter.parse_webhook(
            as_payload(load_fixture(fixture))
        )
        return messages

    def test_messenger_voice_photo_sticker_place_and_files(self) -> None:
        messages = self.parse("messenger_adapter", "messenger_media_webhook.json")

        assert [kinds(m) for m in messages] == [
            [AttachmentKind.AUDIO],
            [AttachmentKind.IMAGE],
            [AttachmentKind.STICKER],
            [AttachmentKind.LOCATION],
            [AttachmentKind.OTHER, AttachmentKind.OTHER],
            [AttachmentKind.OTHER],
        ]
        voice, photo, sticker, place = messages[0], messages[1], messages[2], messages[3]
        assert str(voice.attachments[0].provider_media_id).startswith(
            "https://cdn.fbsbx.com/"
        )
        assert photo.text == "Is this on the menu?"
        # A sticker (the thumbs-up included) is never downloaded.
        assert sticker.attachments[0].provider_media_id is None
        location = place.attachments[0].location
        assert location is not None
        assert location.name == "Freedom Square"
        assert all(m.channel is ChannelKind.MESSENGER for m in messages)

    def test_instagram_voice_photo_reels_stories_and_unsupported(self) -> None:
        messages = self.parse("instagram_adapter", "instagram_media_webhook.json")

        assert [kinds(m) for m in messages] == [
            [AttachmentKind.AUDIO],
            [AttachmentKind.IMAGE],
            [AttachmentKind.OTHER],
            [AttachmentKind.OTHER],
            [AttachmentKind.OTHER],
        ]
        assert str(messages[1].attachments[0].provider_media_id).startswith(
            "https://lookaside.fbsbx.com/ig_messaging_cdn/"
        )
        assert all(m.channel is ChannelKind.INSTAGRAM for m in messages)


def test_a_message_with_nothing_to_answer_is_still_skipped() -> None:
    body: dict[str, Any] = load_fixture("instagram_media_webhook.json")
    body["entry"][0]["messaging"] = [
        {
            "sender": {"id": "1234567890123456"},
            "recipient": {"id": "17841400000000000"},
            "message": {"mid": "m_empty"},
        }
    ]

    assert ChannelsTestbed().instagram_adapter.parse_webhook(as_payload(body)) == []
