from pathlib import Path

import pytest

from app.adapters.recordings.local_recording_storage_adapter import (
    LocalRecordingStorageAdapter,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.conversations.strings import RecordingStoragePath


def test_deletes_recordings_inside_the_root(tmp_path: Path) -> None:
    recordings = tmp_path / "recordings"
    nested_file = recordings / "business_1" / "call-1.mp3"
    nested_file.parent.mkdir(parents=True)
    nested_file.write_bytes(b"ID3")
    storage = LocalRecordingStorageAdapter(recordings)

    storage.delete(RecordingStoragePath("business_1/call-1.mp3"))

    assert not nested_file.exists()
    assert nested_file.parent.exists()


def test_leading_slash_still_means_inside_the_root(tmp_path: Path) -> None:
    recording = tmp_path / "call.ogg"
    recording.write_bytes(b"OggS")
    storage = LocalRecordingStorageAdapter(tmp_path)

    storage.delete(RecordingStoragePath("/call.ogg"))

    assert not recording.exists()


def test_deleting_a_missing_recording_is_not_an_error(tmp_path: Path) -> None:
    storage = LocalRecordingStorageAdapter(tmp_path)

    storage.delete(RecordingStoragePath("never-existed.mp3"))
    storage.delete(RecordingStoragePath("missing-directory/never-existed.mp3"))


@pytest.mark.parametrize(
    "recording_path",
    ["../outside.mp3", "business/../../outside.mp3", "", "/", ".", "a\x00b"],
)
def test_paths_outside_the_root_are_refused(
    tmp_path: Path,
    recording_path: str,
) -> None:
    recordings = tmp_path / "recordings"
    recordings.mkdir()
    outside_file = tmp_path / "outside.mp3"
    outside_file.write_bytes(b"keep me")
    storage = LocalRecordingStorageAdapter(recordings)

    with pytest.raises(ValidationFailedError):
        storage.delete(RecordingStoragePath(recording_path))

    assert outside_file.read_bytes() == b"keep me"


def test_directories_are_not_deleted(tmp_path: Path) -> None:
    (tmp_path / "business_1").mkdir()
    storage = LocalRecordingStorageAdapter(tmp_path)

    with pytest.raises(ValidationFailedError):
        storage.delete(RecordingStoragePath("business_1"))

    assert (tmp_path / "business_1").is_dir()


def test_reads_recordings_with_the_media_type_of_their_extension(
    tmp_path: Path,
) -> None:
    (tmp_path / "business_1").mkdir()
    (tmp_path / "business_1" / "call-1.ogg").write_bytes(b"OggS")
    (tmp_path / "call-2.MP3").write_bytes(b"ID3")
    (tmp_path / "call-3.bin").write_bytes(b"\x00")
    storage = LocalRecordingStorageAdapter(tmp_path)

    ogg = storage.read(RecordingStoragePath("business_1/call-1.ogg"))
    mp3 = storage.read(RecordingStoragePath("/call-2.MP3"))
    unknown = storage.read(RecordingStoragePath("call-3.bin"))

    assert ogg is not None and mp3 is not None and unknown is not None
    assert (ogg.content, str(ogg.media_type)) == (b"OggS", "audio/ogg")
    assert (mp3.content, str(mp3.media_type)) == (b"ID3", "audio/mpeg")
    assert str(unknown.media_type) == "audio/mpeg"


@pytest.mark.parametrize(
    "recording_path",
    ["never-existed.mp3", "missing/never-existed.mp3", "business_1", "../outside.mp3"],
)
def test_missing_directories_and_outside_paths_read_as_no_recording(
    tmp_path: Path,
    recording_path: str,
) -> None:
    recordings = tmp_path / "recordings"
    (recordings / "business_1").mkdir(parents=True)
    (tmp_path / "outside.mp3").write_bytes(b"secret")
    storage = LocalRecordingStorageAdapter(recordings)

    assert storage.read(RecordingStoragePath(recording_path)) is None
