"""Archive keys and the retention of 30 daily and 12 monthly copies."""

from datetime import UTC, datetime, timedelta

from app.schemas.dto.backups import BackupArchive, BackupObjectListing
from app.schemas.typings.backups.constrained_integers import (
    BackupArchiveSize,
    BackupCopyCount,
)
from app.schemas.typings.backups.constrained_strings import BackupObjectKey
from app.utilities.backups.backup_keys import (
    archive_key,
    manifest_key,
    recognize_archives,
)
from app.utilities.backups.backup_retention import select_kept_archives
from tests.backups.backup_fakes import PREFIX, moment


def listing(key: str) -> BackupObjectListing:
    return BackupObjectListing(key=BackupObjectKey(key), size=BackupArchiveSize(10))


def daily_archives(
    last_day: datetime, days: int, per_day: int = 1
) -> list[BackupArchive]:
    keys = [
        archive_key(
            PREFIX,
            moment(
                (last_day - timedelta(days=day, hours=hour)).strftime(
                    "%Y-%m-%dT%H:%M:%S"
                )
            ),
        )
        for day in range(days)
        for hour in range(per_day)
    ]
    return recognize_archives([listing(str(key)) for key in keys], PREFIX)


def test_keys_name_the_month_folder_and_the_utc_start() -> None:
    key = archive_key(PREFIX, moment("2026-10-03T01:07:09"))

    assert key == BackupObjectKey("workshop/2026/10/20261003T010709Z.pgdump.age")
    assert manifest_key(key) == BackupObjectKey(
        "workshop/2026/10/20261003T010709Z.manifest.json"
    )


def test_only_well_formed_archives_under_the_prefix_are_recognized() -> None:
    archives = recognize_archives(
        [
            listing("workshop/2026/10/20261003T010709Z.pgdump.age"),
            listing("workshop/2026/09/20260930T010700Z.pgdump.age"),
            listing("workshop/2026/10/20261003T010709Z.manifest.json"),
            listing("workshop/2026/09/20261001T010700Z.pgdump.age"),  # wrong folder
            listing("workshop/2026/10/20261399T010700Z.pgdump.age"),  # no such day
            listing("workshop/notes.txt"),
            listing("other/2026/10/20261002T010700Z.pgdump.age"),
        ],
        PREFIX,
    )

    assert [str(archive.key) for archive in archives] == [
        "workshop/2026/09/20260930T010700Z.pgdump.age",
        "workshop/2026/10/20261003T010709Z.pgdump.age",
    ]
    assert archives[1].created_at == moment("2026-10-03T01:07:09")


def test_a_year_of_daily_backups_keeps_30_days_and_12_month_ends() -> None:
    last_day = datetime(2026, 10, 3, 1, 7, tzinfo=UTC)
    archives = daily_archives(last_day, days=400)

    kept = select_kept_archives(archives, BackupCopyCount(30), BackupCopyCount(12))

    kept_days = sorted(str(key).split("/")[-1][:8] for key in kept)
    daily = [(last_day - timedelta(days=day)).strftime("%Y%m%d") for day in range(30)]
    month_ends = ["20251130", "20251231", "20260131", "20260228", "20260331"]
    month_ends += ["20260430", "20260531", "20260630", "20260731", "20260831"]
    assert kept_days == sorted(set(daily) | set(month_ends))
    assert len(kept) == 40


def test_several_backups_a_day_keep_only_the_newest_of_each_day() -> None:
    archives = daily_archives(
        datetime(2026, 10, 3, 20, 0, tzinfo=UTC), days=3, per_day=4
    )

    kept = select_kept_archives(archives, BackupCopyCount(2), BackupCopyCount(1))

    assert sorted(str(key).split("/")[-1][:15] for key in kept) == [
        "20261002T200000",
        "20261003T200000",
    ]


def test_retention_keeps_the_newest_even_with_minimal_counts() -> None:
    archives = daily_archives(datetime(2026, 10, 3, tzinfo=UTC), days=5)

    kept = select_kept_archives(archives, BackupCopyCount(1), BackupCopyCount(1))

    assert kept == {archives[-1].key}
    assert select_kept_archives([], BackupCopyCount(1), BackupCopyCount(1)) == set()
