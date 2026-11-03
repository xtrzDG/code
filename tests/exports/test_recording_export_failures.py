"""
A full export never fails on a recording the storage cannot give
(GOV-07): a stored path the storage refuses to look up is listed as
unavailable, and a recording whose reading stops part way is listed as
incomplete with the part read, while the rest of the archive is written.
"""

import io
import json
import zipfile
from typing import Any

from app.schemas.dto.call_recordings import (
    RecordingAudio,
    RecordingByteRange,
    RecordingLocation,
    RecordingPart,
)
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.conversations.constrained_strings import RecordingMediaType
from app.use_cases.exports.recording_archive import CHUNK_BYTES, RecordingArchive
from tests.channels.recording_storage_fakes import InMemoryRecordingStorage
from tests.compliance.two_tenants import TwoTenants, seed_two_tenants

AUDIO: bytes = bytes(range(256)) * (2 * CHUNK_BYTES // 256)


class RefusingStorage(InMemoryRecordingStorage):
    """Refuses every stored path (one it does not keep)."""

    def read(
        self,
        location: RecordingLocation,
        wanted: RecordingByteRange | None = None,
    ) -> RecordingPart | None:
        raise ValidationFailedError(f"Invalid recording path {location.path!r}.")


class BreakingStorage(InMemoryRecordingStorage):
    """Gives the first megabyte, then cannot be reached any more."""

    def read(
        self,
        location: RecordingLocation,
        wanted: RecordingByteRange | None = None,
    ) -> RecordingPart | None:
        offset = None if wanted is None else wanted.first_byte
        if offset is not None and int(offset) > 0:
            raise ExternalServiceError("Object storage unreachable.")

        return super().read(location, wanted)


def written(
    tenants: TwoTenants, storage: InMemoryRecordingStorage
) -> tuple[dict[str, Any], dict[str, bytes]]:
    """recordings.json by call id, and every file of the archive."""

    call = tenants.visitor.conversation_call
    assert call.recording_path is not None
    storage.store(
        RecordingLocation(business_id=call.business_id, path=call.recording_path),
        RecordingAudio(content=AUDIO, media_type=RecordingMediaType("audio/ogg")),
    )
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w") as archive:
        RecordingArchive(tenants.testbed.call_repo, storage).write(
            archive, tenants.business.id
        )
    with zipfile.ZipFile(io.BytesIO(target.getvalue())) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}

    listed = {entry["call_id"]: entry for entry in json.loads(files["recordings.json"])}
    return listed, files


def test_a_path_the_storage_refuses_is_listed_never_a_failure() -> None:
    tenants = seed_two_tenants()

    listed, files = written(tenants, RefusingStorage())

    entry = listed[str(tenants.visitor.conversation_call.id)]
    assert (entry["status"], entry["file"]) == ("unavailable", None)
    assert entry["download_path"].endswith("/recording")
    assert not any(name.startswith("recordings/") for name in files)


def test_a_reading_stopped_part_way_keeps_the_part_and_says_so() -> None:
    tenants = seed_two_tenants()
    call = tenants.visitor.conversation_call

    listed, files = written(tenants, BreakingStorage())

    entry = listed[str(call.id)]
    assert (entry["status"], entry["file"]) == (
        "incomplete",
        f"recordings/{call.id}.ogg",
    )
    assert entry["total_bytes"] == len(AUDIO)
    assert files[f"recordings/{call.id}.ogg"] == AUDIO[:CHUNK_BYTES]
