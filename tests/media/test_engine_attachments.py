"""
The engine and what customers send besides text: a sticker or file alone is
answered with the request to write in the customer's language (ka, ru, en,
he) without asking the model; a voice note's words and a place reach the
model inside the customer's fence; photos are shown as pictures.
"""

import json
from typing import Any

import pytest

from app.adapters.llm.anthropic_llm_adapter import (
    UNAVAILABLE_PHOTO_NOTE,
    build_anthropic_messages,
)
from app.adapters.llm.media_resolving_llm_adapter import (
    EARLIER_PHOTO_NOTE,
    GONE_PHOTO_NOTE,
    MediaResolvingLlmAdapter,
)
from app.adapters.llm.openai_input_items import build_openai_input_items
from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.media import AttachmentKind, AttachmentProblem
from app.schemas.domain.message_media import MessageAttachment, SharedLocation
from app.schemas.dto.conversations import AssistantReply, InboundMessage
from app.schemas.dto.media import MediaLocation, StoredMediaFile
from app.schemas.typings.conversations.strings import (
    ChannelUserId,
    LlmProviderPayload,
    MessageText,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.media.constrained_floats import Latitude, Longitude
from app.schemas.typings.media.constrained_strings import MessageMediaType
from app.schemas.typings.media.strings import (
    LocationName,
    MediaStoragePath,
    TranscribedVoiceText,
)
from app.utilities.conversations.assistant_texts.attachment_notice_texts import (
    CANNOT_READ_ATTACHMENT,
)
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.business_setups import ISRAEL
from tests.brain.engine_helpers import requests_of, user_turn_text
from tests.brain.fenced_text import fenced_texts
from tests.brain.scripted_turns import say, scripted
from tests.media.media_fakes import InMemoryMediaStorage, jpeg_bytes

STICKER: MessageAttachment = MessageAttachment(
    kind=AttachmentKind.STICKER, problem=AttachmentProblem.UNSUPPORTED_KIND
)


def send(world: BrainWorld, text: str, *attachments: MessageAttachment) -> Any:
    return world.pipeline.start(
        InboundMessage(
            business_id=world.business.id,
            channel=ChannelKind.WHATSAPP,
            channel_user_id=ChannelUserId("995555123456"),
            text=MessageText(text),
            attachments=list(attachments),
        )
    )


def notice(language: str) -> str:
    return str(CANNOT_READ_ATTACHMENT.values[LanguageTag(language)])


def stored_photo(world: BrainWorld, storage: InMemoryMediaStorage, name: str) -> Any:
    path = MediaStoragePath(f"message-media/{world.business.id}/{name}.jpg")
    storage.store(
        MediaLocation(business_id=world.business.id, path=path),
        StoredMediaFile(
            content=jpeg_bytes(), media_type=MessageMediaType("image/jpeg")
        ),
    )
    return MessageAttachment(
        kind=AttachmentKind.IMAGE,
        storage_path=path,
        media_type=MessageMediaType("image/jpeg"),
    )


def user_blocks(payload: str) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = json.loads(payload)["content"]
    return content


class TestAttachmentNotice:
    @pytest.mark.parametrize(
        ("opening", "language"),
        [
            (None, "ka"),
            ("Здравствуйте, у вас есть столик?", "ru"),
            ("Hello, do you have a table?", "en"),
        ],
    )
    def test_a_sticker_alone_is_answered_with_a_request_to_write(
        self, opening: str | None, language: str
    ) -> None:
        world = build_world(scripted(say("Yes, we do.")))
        if opening is not None:
            send(world, opening)
        asked_before = len(requests_of(world))

        reply: AssistantReply = send(world, "", STICKER)

        assert reply.text is not None
        assert str(reply.text).endswith(notice(language))
        # The model was not asked: nothing in the message can be read.
        assert len(requests_of(world)) == asked_before

    def test_hebrew_customers_are_asked_in_hebrew(self) -> None:
        world = build_world(scripted(say("כן")), ISRAEL)

        reply: AssistantReply = send(world, "", STICKER)

        assert reply.text is not None
        assert notice("he") in str(reply.text)
        assert requests_of(world) == []

    def test_a_sticker_with_words_is_answered_by_the_model(self) -> None:
        world = build_world(scripted(say("We are open until 23:00.")))

        reply: AssistantReply = send(world, "Until when are you open?", STICKER)

        assert str(reply.text).endswith("We are open until 23:00.")
        [request] = requests_of(world)
        turn = user_turn_text(request.transcript[-1])
        assert "[Sticker]" in fenced_texts(turn)[-1]


class TestReadableAttachments:
    def test_a_voice_note_reaches_the_model_transcribed_inside_the_fence(
        self,
    ) -> None:
        world = build_world(scripted(say("Да, есть.")))
        voice = MessageAttachment(
            kind=AttachmentKind.AUDIO,
            transcript=TranscribedVoiceText("Есть столик на четверых?"),
        )

        reply: AssistantReply = send(world, "", voice)

        assert reply.language == "ru"
        [request] = requests_of(world)
        [fenced] = fenced_texts(user_turn_text(request.transcript[-1]))
        assert fenced == "[Voice message, transcribed]\nЕсть столик на четверых?"
        [customer, _] = world.messages(reply.conversation_id)
        assert customer.author is MessageAuthor.CUSTOMER
        assert customer.text == ""
        assert customer.attachments == [voice]

    def test_a_place_reaches_the_model_with_its_map_link(self) -> None:
        world = build_world(scripted(say("It's a 10-minute walk.")))
        place = MessageAttachment(
            kind=AttachmentKind.LOCATION,
            location=SharedLocation(
                latitude=Latitude(41.693438),
                longitude=Longitude(44.801525),
                name=LocationName("Freedom Square"),
            ),
        )

        send(world, "How do I get to you?", place)

        [request] = requests_of(world)
        [fenced] = fenced_texts(user_turn_text(request.transcript[-1]))
        assert fenced.startswith("[Location] 41.693438, 44.801525 (Freedom Square)")
        assert "https://maps.google.com/?q=41.693438,44.801525" in fenced
        assert fenced.endswith("How do I get to you?")


class TestPhotos:
    def world_with_photos(self, replies: int) -> tuple[BrainWorld, Any, Any]:
        inner: ScriptedLlmAdapter = scripted(*[say("Nice!") for _ in range(replies)])
        storage = InMemoryMediaStorage()
        world = build_world(MediaResolvingLlmAdapter(inner, storage))
        return world, inner, storage

    def test_the_model_sees_the_picture_and_the_transcript_keeps_a_reference(
        self,
    ) -> None:
        world, inner, storage = self.world_with_photos(1)
        photo = stored_photo(world, storage, "dish")

        reply = send(world, "Is this on your menu?", photo)

        [request] = inner.requests
        sent = user_blocks(request.transcript[-1])
        [image] = [block for block in sent if block["type"] == "image"]
        assert image["source"]["type"] == "base64"
        assert image["source"]["media_type"] == "image/jpeg"
        [stored_turn] = [
            turn
            for turn in world.turns(reply.conversation_id)
            if '"image"' in str(turn.payload)
        ]
        assert '"stored_media"' in str(stored_turn.payload)
        assert '"base64"' not in str(stored_turn.payload)

    def test_older_photos_become_a_note_and_a_purged_one_says_so(self) -> None:
        world, inner, storage = self.world_with_photos(6)
        photos = [stored_photo(world, storage, f"p{index}") for index in range(5)]
        for index, photo in enumerate(photos):
            send(world, f"Photo {index}", photo)
        storage.files.clear()
        gone = MessageAttachment(
            kind=AttachmentKind.IMAGE,
            storage_path=MediaStoragePath(f"message-media/{world.business.id}/x.jpg"),
            media_type=MessageMediaType("image/jpeg"),
        )
        send(world, "And this one?", gone)

        last = inner.requests[-1]
        texts = [
            block.get("text")
            for payload in last.transcript
            if json.loads(payload)["role"] == "user"
            for block in user_blocks(payload)
        ]
        assert texts.count(EARLIER_PHOTO_NOTE) == 2
        assert texts.count(GONE_PHOTO_NOTE) == 4


class TestProviderPictures:
    def turn_with(self, *sources: dict[str, str]) -> LlmProviderPayload:
        content: list[dict[str, object]] = [{"type": "text", "text": "Look"}]
        content.extend({"type": "image", "source": source} for source in sources)
        return LlmProviderPayload(json.dumps({"role": "user", "content": content}))

    resolved: dict[str, str] = {
        "type": "base64",
        "media_type": "image/png",
        "data": "aGVsbG8=",
    }
    unresolved: dict[str, str] = {
        "type": "stored_media",
        "business_id": "b",
        "path": "message-media/b/p.png",
        "media_type": "image/png",
    }

    def test_openai_gets_input_images_as_data_urls(self) -> None:
        [item] = build_openai_input_items(
            [self.turn_with(self.resolved, self.unresolved)]
        )

        assert item["content"] == [
            {"type": "input_text", "text": "Look"},
            {
                "type": "input_image",
                "image_url": "data:image/png;base64,aGVsbG8=",
                "detail": "auto",
            },
        ]

    def test_anthropic_gets_image_blocks_and_a_note_for_unresolved_ones(
        self,
    ) -> None:
        [message] = build_anthropic_messages(
            [self.turn_with(self.resolved, self.unresolved)]
        )

        assert message["content"] == [
            {"type": "text", "text": "Look"},
            {"type": "image", "source": self.resolved},
            {"type": "text", "text": UNAVAILABLE_PHOTO_NOTE},
        ]

    def test_a_transcript_without_photos_passes_through_untouched(self) -> None:
        inner = scripted(say("Hi"))
        adapter = MediaResolvingLlmAdapter(inner, InMemoryMediaStorage())
        world = build_world(adapter)

        send(world, "Hello")

        [request] = inner.requests
        assert all("stored_media" not in str(turn) for turn in request.transcript)
