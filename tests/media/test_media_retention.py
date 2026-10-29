"""
Customer files are kept as long as call recordings: the daily retention
purge removes old ones (the transcript stays, the message says the file is
gone, each removal is audited), and erasing a customer removes theirs.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.media import AttachmentKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.message_media import MessageAttachment, MessageMediaDocument
from app.schemas.dto.compliance import ContactDataCommand, PurgeExpiredRecordingsCommand
from app.schemas.dto.media import MediaLocation, StoredMediaFile
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.media.constrained_integers import MediaByteCount
from app.schemas.typings.media.constrained_strings import MessageMediaType
from app.schemas.typings.media.prefixed_id import MessageMediaId
from app.schemas.typings.media.strings import MediaStoragePath
from app.transformers.conversations.message_view_transformer import (
    MessageViewTransformer,
)
from app.use_cases.compliance.purge_expired_message_media_use_case import (
    PurgeExpiredMessageMediaUseCase,
)
from tests.channels.telegram_updates import connect_bot, post_update
from tests.channels.testbed import ChannelsTestbed
from tests.compliance.customer_records import seed_customers
from tests.media.inbound_media_steps import telegram_update
from tests.media.media_fakes import jpeg_bytes, ogg_opus_bytes

DAY_SECONDS: int = 24 * 3600


def purge_of(testbed: ChannelsTestbed) -> PurgeExpiredMessageMediaUseCase:
    return PurgeExpiredMessageMediaUseCase(
        business_repo=testbed.business_repo,
        message_media_repo=testbed.message_media_repo,
        message_repo=testbed.message_repo,
        media_storage=testbed.media_storage,
        audit_log_repo=testbed.audit_log_repo,
        wall_clock=testbed.wall_clock,
    )


def stored_media(
    testbed: ChannelsTestbed, business_id: BusinessId
) -> list[MessageMediaDocument]:
    return testbed.message_media_repo.list_created_before(
        business_id, Microseconds(2**62)
    )


class TestRetentionPurge:
    def setup_voice_note(self) -> tuple[ChannelsTestbed, BusinessDocument]:
        testbed = ChannelsTestbed()
        business, channel = connect_bot(testbed)
        testbed.media_fetcher.files["voice-file-0001"] = ogg_opus_bytes()
        testbed.voice_transcriber.texts = ["A table for four, please."]
        post_update(testbed, channel, telegram_update(0))
        testbed.run_worker()
        return testbed, business

    def test_files_older_than_the_retention_are_removed(self) -> None:
        testbed, business = self.setup_voice_note()
        retention_days = int(business.recording_retention_days)
        [media] = stored_media(testbed, business.id)

        testbed.clock.advance((retention_days - 1) * DAY_SECONDS)
        early = purge_of(testbed).run(PurgeExpiredRecordingsCommand(business_id=None))
        assert int(early.deleted_files) == 0

        testbed.clock.advance(2 * DAY_SECONDS)
        result = purge_of(testbed).run(PurgeExpiredRecordingsCommand(business_id=None))

        assert int(result.deleted_files) == 1
        assert testbed.media_storage.files == {}
        assert stored_media(testbed, business.id) == []
        message = testbed.message_repo.get(
            business.id,
            media.message_id,
        )
        assert message is not None
        [voice] = message.attachments
        assert voice.media_deleted_at is not None
        assert voice.transcript == "A table for four, please."
        view = MessageViewTransformer().transform(message)
        assert view.attachments[0].is_media_deleted is True
        assert view.attachments[0].media_id is None
        assert view.attachments[0].transcript == "A table for four, please."
        purges = [
            entry
            for entry in testbed.audit_log_repo.list_by_business(business.id)
            if entry.action is AuditAction.RETENTION_PURGE
            and str(entry.entity) == "message_media"
        ]
        assert [str(entry.entity_id) for entry in purges] == [str(media.id)]
        assert purges[0].actor_id is None

        again = purge_of(testbed).run(PurgeExpiredRecordingsCommand(business_id=None))
        assert int(again.deleted_files) == 0

    def test_one_business_can_be_purged_alone(self) -> None:
        testbed, business = self.setup_voice_note()
        testbed.clock.advance(365 * DAY_SECONDS)

        missing = purge_of(testbed).run(
            PurgeExpiredRecordingsCommand(
                business_id=testbed.add_business(testbed.add_user("other-owner")).id
            )
        )
        assert int(missing.deleted_files) == 0
        assert len(testbed.media_storage.files) == 1

        mine = purge_of(testbed).run(
            PurgeExpiredRecordingsCommand(business_id=business.id)
        )
        assert int(mine.deleted_files) == 1


def test_erasing_a_customer_removes_their_files() -> None:
    customers = seed_customers()
    testbed = customers.testbed
    giorgi = customers.giorgi
    message = giorgi.messages[0]
    path = MediaStoragePath(f"message-media/{customers.business.id}/giorgi.jpg")
    media_id = MessageMediaId(f"message_media_{'2' * 8}-2222-5222-8222-{'2' * 12}")
    location = MediaLocation(business_id=customers.business.id, path=path)
    testbed.media_storage.store(
        location,
        StoredMediaFile(
            content=jpeg_bytes(), media_type=MessageMediaType("image/jpeg")
        ),
    )
    now = testbed.clock.now_microseconds()
    testbed.message_media_repo.save(
        MessageMediaDocument(
            id=media_id,
            business_id=customers.business.id,
            message_id=message.id,
            kind=AttachmentKind.IMAGE,
            storage_path=path,
            media_type=MessageMediaType("image/jpeg"),
            byte_count=MediaByteCount(len(jpeg_bytes())),
            created_at=now,
            updated_at=now,
        )
    )
    message.attachments = [
        MessageAttachment(
            kind=AttachmentKind.IMAGE,
            media_id=media_id,
            storage_path=path,
            media_type=MessageMediaType("image/jpeg"),
        )
    ]
    testbed.message_repo.save(message)

    testbed.delete_contact_data.run(
        ContactDataCommand(
            user_id=customers.owner_id,
            business_id=customers.business.id,
            contact_id=giorgi.contact.id,
        )
    )

    assert testbed.media_storage.read(location) is None
    assert testbed.message_media_repo.get(customers.business.id, media_id) is None
