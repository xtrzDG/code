"""
The download of a full export of 48 MiB: the API reads the sealed archive
from the bucket in ranges, opens it segment by segment and hands the
response a megabyte at a time, so its memory peaks far below the archive
(traced allocations, under 12 MiB; about 8 MiB measured: one range of four
segments, one segment filling, one waiting, one opened) while every byte
comes back. Reading and opening the archive whole, as the download did
before, took about twice the archive (96 MiB here).
"""

import hashlib
import os
import tempfile
import tracemalloc

from app.adapters.exports.encrypted_object_export_archive_storage_adapter import (
    READ_WINDOW_BYTES,
    EncryptedObjectExportArchiveStorageAdapter,
)
from app.schemas.typings.privacy.strings import ExportArchivePath
from tests.compliance.two_tenants import seed_two_tenants
from tests.privacy.business_export_bed import EXPORT_KEY, BusinessExportBed

ARCHIVE_BYTES: int = 48 * 1024 * 1024
PIECE_BYTES: int = 1024 * 1024
PEAK_BUDGET_BYTES: int = 12 * 1024 * 1024


def store_big_archive(bed: BusinessExportBed, path: ExportArchivePath) -> str:
    """A 48 MiB archive of random bytes in place of the real one; its hash."""

    digest = hashlib.sha256()
    storage = EncryptedObjectExportArchiveStorageAdapter(
        client=bed.objects, master_secret=EXPORT_KEY
    )
    with tempfile.TemporaryFile() as archive:
        for _ in range(ARCHIVE_BYTES // PIECE_BYTES):
            piece: bytes = os.urandom(PIECE_BYTES)
            digest.update(piece)
            archive.write(piece)
        storage.store(bed.tenants.business.id, path, archive)
    return digest.hexdigest()


def test_downloading_48_mib_peaks_below_12_mib() -> None:
    bed = BusinessExportBed(seed_two_tenants())
    ready = bed.ready_export()
    stored = bed.export_repo.get(bed.tenants.business.id, ready.id)
    assert stored is not None and stored.archive_path is not None
    expected: str = store_big_archive(bed, stored.archive_path)
    link = bed.link(ready.id)
    digest = hashlib.sha256()
    received, largest_piece = 0, 0

    tracemalloc.start()
    try:
        download = bed.download(str(link.download_path))
        for piece in download.pieces:
            digest.update(piece)
            received += len(piece)
            largest_piece = max(largest_piece, len(piece))
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert received == ARCHIVE_BYTES
    assert digest.hexdigest() == expected
    assert largest_piece <= PIECE_BYTES
    assert peak < PEAK_BUDGET_BYTES, f"peak {peak / 2**20:.1f} MiB"
    assert ARCHIVE_BYTES > 3 * READ_WINDOW_BYTES
