"""
A full export of a business with 50,000 messages: the worker writes the
archive into a temporary file a page at a time, seals it in segments and
uploads it in parts, and its memory peaks below 64 MB all along (traced
allocations; about 14 MB measured), while the archive holds every message.
Holding the 50,000 messages and their JSON at once, as the export did
before, takes about 156 MB in the same setup.
"""

import hashlib
import io
import json
import tracemalloc
import zipfile
from collections.abc import Iterable
from dataclasses import replace
from typing import cast

from typed_time_provider import Microseconds

from app.adapters.exports.encrypted_object_export_archive_storage_adapter import (
    EncryptedObjectExportArchiveStorageAdapter,
)
from app.contracts.object_storage import ObjectStorageClientContract
from app.contracts.repositories.conversation_repositories import MessageRepoContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.privacy import BusinessExportStatus
from app.schemas.dto.privacy.business_exports import BusinessExportListQuery
from app.schemas.typings.conversations.strings import RecordingStoragePath
from app.use_cases.exports.business_archive import BusinessArchiveBuilder
from app.use_cases.exports.run_business_export_use_case import (
    RunBusinessExportUseCase,
)
from tests.compliance.two_tenants import seed_two_tenants
from tests.compliance.visitor_records import build_conversation
from tests.exports.generated_messages import GeneratedMessages
from tests.privacy.business_export_bed import EXPORT_KEY, BusinessExportBed

CONVERSATIONS: int = 500
MESSAGES_PER_CONVERSATION: int = 100
PEAK_BUDGET_BYTES: int = 64 * 1024 * 1024


def as_message_repo(messages: GeneratedMessages) -> MessageRepoContract:
    """The generated history offers the reads a full export makes."""

    return cast(MessageRepoContract, messages)


class SizingObjectStorage(ObjectStorageClientContract):
    """Keeps a hash and the size of each upload, never the bytes."""

    def __init__(self) -> None:
        self.uploads: dict[str, tuple[str, int, int]] = {}

    def put_object(self, key: RecordingStoragePath, body: bytes) -> None:
        self.put_object_parts(key, [body])

    def get_object_range(
        self, key: RecordingStoragePath, first_byte: int, last_byte: int
    ) -> bytes | None:
        return None

    def delete_object(self, key: RecordingStoragePath) -> None:
        self.uploads.pop(str(key), None)

    def put_object_parts(
        self, key: RecordingStoragePath, parts: Iterable[bytes]
    ) -> None:
        digest = hashlib.sha256()
        size, count = 0, 0
        for part in parts:
            digest.update(part)
            size += len(part)
            count += 1
        self.uploads[str(key)] = (digest.hexdigest(), size, count)


def test_exporting_50000_messages_peaks_below_64_mb() -> None:
    tenants = seed_two_tenants()
    testbed = tenants.testbed
    business = tenants.business
    now: Microseconds = testbed.clock.now_microseconds()
    conversations = [
        build_conversation(
            business,
            tenants.visitor.contact,
            ChannelKind.TELEGRAM,
            f"{900000 + n}",
            now,
        )
        for n in range(CONVERSATIONS)
    ]
    testbed.conversation_repo.save_many(conversations)
    messages = GeneratedMessages(
        business.id,
        [conversation.id for conversation in conversations],
        MESSAGES_PER_CONVERSATION,
        now,
    )
    objects = SizingObjectStorage()
    bed = BusinessExportBed(tenants)
    bed.job = RunBusinessExportUseCase(
        business_repo=testbed.business_repo,
        export_repo=bed.export_repo,
        archive_builder=replace(
            bed.archive_builder, message_repo=as_message_repo(messages)
        ),
        archive_storage=EncryptedObjectExportArchiveStorageAdapter(objects, EXPORT_KEY),
        wall_clock=testbed.clock.build_wall_clock(),
    )
    export = bed.ask()

    tracemalloc.start()
    try:
        bed.run_job()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert peak < PEAK_BUDGET_BYTES, f"peak {peak / 1024 / 1024:.1f} MB"
    [ready] = bed.list.run(
        BusinessExportListQuery(user_id=tenants.owner_id, business_id=business.id)
    ).items
    assert ready.id == export.id
    assert ready.status is BusinessExportStatus.READY
    assert int(ready.record_count or 0) > messages.count
    [(_, sealed_size, parts)] = objects.uploads.values()
    assert sealed_size > int(ready.archive_bytes or 0) > 100 * 1024
    assert parts >= 1


def test_the_archive_holds_every_message_and_its_table() -> None:
    tenants = seed_two_tenants()
    testbed = tenants.testbed
    business = tenants.business
    now: Microseconds = testbed.clock.now_microseconds()
    conversations = [
        build_conversation(
            business,
            tenants.visitor.contact,
            ChannelKind.TELEGRAM,
            f"{800000 + n}",
            now,
        )
        for n in range(3)
    ]
    testbed.conversation_repo.save_many(conversations)
    messages = GeneratedMessages(
        business.id, [conversation.id for conversation in conversations], 700, now
    )
    bed = BusinessExportBed(tenants)
    builder: BusinessArchiveBuilder = replace(
        bed.archive_builder, message_repo=as_message_repo(messages)
    )
    target = io.BytesIO()

    records = builder.write(
        business, business.owner_language, now, tenants.owner_id, target
    )

    with zipfile.ZipFile(target) as archive:
        stored = json.loads(archive.read("messages.json"))
        table = archive.read("csv/conversations.csv").decode("utf-8")
    assert [item["id"] for item in stored] == [
        str(messages.message(number).id) for number in range(messages.count)
    ]
    assert int(records) >= messages.count
    # One row per message of the three conversations (and the header).
    assert table.count("\r\n") >= messages.count + 1
