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
