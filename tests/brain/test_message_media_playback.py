"""Opening a voice note or photo a customer sent, from the conversation card."""

from typing import Any
from uuid import NAMESPACE_URL, uuid5

from fastapi.testclient import TestClient
from typed_time_provider import Microseconds

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.media import AttachmentKind
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.message_media import MessageMediaDocument
from app.schemas.dto.media import MediaLocation, StoredMediaFile
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.media.constrained_integers import MediaByteCount
from app.schemas.typings.media.constrained_strings import MessageMediaType
from app.schemas.typings.media.prefixed_id import MessageMediaId
from app.schemas.typings.media.strings import MediaStoragePath
from app.schemas.typings.users.prefixed_id import UserId
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.cabinet_fakes import CabinetStorage, UnusedMenuExtractor
from tests.brain.cabinet_http import bearer, build_cabinet_client
from tests.brain.scripted_turns import say, scripted
from tests.media.media_fakes import jpeg_bytes, ogg_opus_bytes


def media_id_of(name: str) -> MessageMediaId:
    return MessageMediaId(uuid5(NAMESPACE_URL, f"media-route|{name}"))


class MediaCard:
    def __init__(self, world: BrainWorld) -> None:
        self.world = world
        self.storage = CabinetStorage()
        self.client: TestClient = build_cabinet_client(
            world,
            UnusedMenuExtractor(),
            {"owner": world.owner_id, "staff": world.staff_id, "stranger": UserId()},
            self.storage,
        )

    def add_media(
        self,
        name: str,
        content: bytes | None,
        media_type: str = "audio/ogg",
        business_id: BusinessId | None = None,
    ) -> MessageMediaDocument:
        reply = self.world.send("Hi")
        [message, _] = self.world.messages(reply.conversation_id)[-2:]
        owner = business_id or self.world.business.id
        path = MediaStoragePath(f"message-media/{owner}/{name}")
        if content is not None:
            self.storage.media_storage.store(
                MediaLocation(business_id=owner, path=path),
                StoredMediaFile(
                    content=content, media_type=MessageMediaType(media_type)
                ),
            )
        now = Microseconds(self.world.clock.now_nanoseconds() // 1000)
        media = MessageMediaDocument(
            id=media_id_of(name),
            business_id=owner,
            message_id=message.id,
            kind=(
                AttachmentKind.AUDIO
                if media_type.startswith("audio/")
                else AttachmentKind.IMAGE
            ),
            storage_path=path,
            media_type=MessageMediaType(media_type),
            byte_count=MediaByteCount(len(content or b"x")),
            created_at=now,
            updated_at=now,
        )
        self.storage.message_media_repo.save(media)
        return media

    def open(self, media_id: object, token: str = "staff") -> Any:
        return self.client.get(
            f"/v1/businesses/{self.world.business.id}/media/{media_id}",
            headers=bearer(token),
        )

    def views(self) -> list[AuditLogEntryDocument]:
        return [
            entry
            for entry in self.world.audit_log_repo.list_by_business(
                self.world.business.id
            )
            if entry.entity == "message_media"
        ]


def test_owner_and_staff_open_files_and_each_opening_is_audited() -> None:
    card = MediaCard(build_world(scripted(say("a"), say("b"))))
    voice = card.add_media("voice.ogg", ogg_opus_bytes())
    photo = card.add_media("dish.jpg", jpeg_bytes(), "image/jpeg")

    heard = card.open(voice.id, token="staff")
    seen = card.open(photo.id, token="owner")

    assert (heard.status_code, heard.content) == (200, ogg_opus_bytes())
    assert heard.headers["content-type"] == "audio/ogg"
    assert (seen.status_code, seen.content) == (200, jpeg_bytes())
    assert seen.headers["content-type"] == "image/jpeg"
    for response in (heard, seen):
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["content-disposition"] == "inline"
        assert "sandbox" in response.headers["content-security-policy"]
    views = card.views()
    assert [(entry.action, entry.actor_id) for entry in views] == [
        (AuditAction.VIEW, card.world.staff_id),
        (AuditAction.VIEW, card.world.owner_id),
    ]
    assert [str(entry.entity_id) for entry in views] == [str(voice.id), str(photo.id)]
    assert views[0].ip_address == "testclient"


def test_purged_unknown_foreign_and_unauthorized_files_are_not_found() -> None:
    card = MediaCard(build_world(scripted(say("a"), say("b"), say("c"))))
    purged = card.add_media("purged.ogg", None)
    foreign = card.add_media("foreign.ogg", ogg_opus_bytes(), business_id=BusinessId())
    kept = card.add_media("kept.ogg", ogg_opus_bytes())

    responses = [
        card.open(purged.id),
        card.open(foreign.id),
        card.open(media_id_of("never-sent")),
        card.open("not-a-media-id"),
        card.open(kept.id, token="stranger"),
    ]

    assert [response.status_code for response in responses] == [404] * 5
    assert "retention" in responses[0].json()["message"]
    assert "retention" in responses[1].json()["message"]
    assert card.views() == []
