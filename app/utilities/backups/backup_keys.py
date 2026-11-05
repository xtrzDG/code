"""
Where archives live in the bucket and how they are recognized again.

    <prefix><YYYY>/<MM>/<YYYYMMDD>T<HHMMSS>Z.pgdump.age     the archive
    <prefix><YYYY>/<MM>/<YYYYMMDD>T<HHMMSS>Z.manifest.json  its manifest

The time (UTC) in the name is when the backup started, so the bucket's
listing is the backup history in order, and retention never needs the
storage's own timestamps (which a copy or a restore of the bucket resets).
"""

import re
from datetime import UTC, datetime

from typed_time_provider import Microseconds

from app.schemas.dto.backups import BackupArchive, BackupObjectListing
from app.schemas.typings.backups.constrained_strings import (
    BackupObjectKey,
    BackupObjectPrefix,
)

ARCHIVE_SUFFIX: str = ".pgdump.age"
MANIFEST_SUFFIX: str = ".manifest.json"
STAMP_FORMAT: str = "%Y%m%dT%H%M%SZ"
MICROSECONDS_PER_SECOND: int = 1_000_000


def archive_key(
    prefix: BackupObjectPrefix, started_at: Microseconds
) -> BackupObjectKey:
    moment: datetime = to_datetime(started_at)
    return BackupObjectKey(
        f"{prefix}{moment:%Y}/{moment:%m}/{moment.strftime(STAMP_FORMAT)}"
        f"{ARCHIVE_SUFFIX}"
    )


def manifest_key(archive: BackupObjectKey) -> BackupObjectKey:
    return BackupObjectKey(str(archive).removesuffix(ARCHIVE_SUFFIX) + MANIFEST_SUFFIX)


def recognize_archives(
    listings: list[BackupObjectListing],
    prefix: BackupObjectPrefix,
) -> list[BackupArchive]:
    """
    The archives among the listed objects, oldest first. Anything else
    under the prefix (manifests, an operator's notes, foreign files) is
    not an archive and is never touched by retention.
    """

    pattern: re.Pattern[str] = re.compile(
        re.escape(str(prefix))
        + r"(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/"
        + r"(?P<stamp>[0-9]{8}T[0-9]{6}Z)"
        + re.escape(ARCHIVE_SUFFIX)
    )
    archives: list[BackupArchive] = []
    for listing in listings:
        match = pattern.fullmatch(str(listing.key))
        if match is None:
            continue

        try:
            moment = datetime.strptime(match["stamp"], STAMP_FORMAT).replace(tzinfo=UTC)
        except ValueError:
            continue

        if (f"{moment:%Y}", f"{moment:%m}") != (match["year"], match["month"]):
            continue

        archives.append(
            BackupArchive(
                key=listing.key,
                manifest_key=manifest_key(listing.key),
                created_at=Microseconds(
                    int(moment.timestamp()) * MICROSECONDS_PER_SECOND
                ),
            )
        )

    return sorted(archives, key=lambda archive: int(archive.created_at))


def to_datetime(moment: Microseconds) -> datetime:
    return datetime.fromtimestamp(int(moment) // MICROSECONDS_PER_SECOND, UTC)
