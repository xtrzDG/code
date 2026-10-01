"""Migration file names, checksums and the directory source (no database)."""

import hashlib
from pathlib import Path

import pytest

from app.adapters.storage.postgres.sql_file_migration_source_adapter import (
    SqlFileMigrationSourceAdapter,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.storage.constrained_strings import SchemaMigrationName
from app.utilities.storage.schema_migration_files import (
    compute_migration_checksum,
    find_duplicate_versions,
    migration_name_from_file_name,
    migration_version,
    normalize_migration_sql,
)
from tests.storage.storage_testing import MIGRATIONS_DIRECTORY


def test_file_names_become_typed_migration_names() -> None:
    name = migration_name_from_file_name("0001_document_collections.sql")

    assert name == "0001_document_collections"
    assert type(name) is SchemaMigrationName
    assert migration_version(name) == "0001"


@pytest.mark.parametrize(
    "file_name",
    [
        "1_short_version.sql",
        "0001-dash.sql",
        "0001_UpperCase.sql",
        "0001_.sql",
        "0001_ünïcode.sql",
        "0001_document_collections.SQL",
        "0001_trailing.sql.bak",
        "0001_newline\n.sql",
    ],
)
def test_misnamed_files_are_rejected(file_name: str) -> None:
    with pytest.raises(ValidationFailedError):
        migration_name_from_file_name(file_name)


def test_checksum_ignores_line_ending_style_only() -> None:
    unix_text = "create table a (id int);\nselect 1;\n"

    assert compute_migration_checksum(unix_text) == compute_migration_checksum(
        unix_text.replace("\n", "\r\n")
    )
    assert compute_migration_checksum(unix_text) == compute_migration_checksum(
        unix_text.replace("\n", "\r")
    )
    assert compute_migration_checksum(unix_text) != compute_migration_checksum(
        unix_text + " "
    )
    assert compute_migration_checksum(unix_text) == (
        hashlib.sha256(unix_text.encode("utf-8")).hexdigest()
    )
    assert normalize_migration_sql("a\r\nb\rc") == "a\nb\nc"


def test_duplicate_versions_are_found() -> None:
    names = [
        SchemaMigrationName("0001_a"),
        SchemaMigrationName("0002_b"),
        SchemaMigrationName("0002_c"),
        SchemaMigrationName("0003_d"),
        SchemaMigrationName("0003_e"),
    ]

    assert find_duplicate_versions(names) == ["0002", "0003"]
    assert find_duplicate_versions(names[:2]) == []


def test_directory_source_reads_sql_files_in_version_order(tmp_path: Path) -> None:
    (tmp_path / "0010_later.sql").write_text("select 10;\n", encoding="utf-8")
    (tmp_path / "0002_earlier.sql").write_text(
        "-- გამარჯობა\r\nselect 2;\r\n", encoding="utf-8"
    )
    (tmp_path / "README.md").write_text("# notes\n", encoding="utf-8")
    (tmp_path / "0003_directory.sql").mkdir()

    scripts = SqlFileMigrationSourceAdapter(tmp_path).load_scripts()

    assert [script.name for script in scripts] == ["0002_earlier", "0010_later"]
    assert scripts[0].sql == "-- გამარჯობა\nselect 2;\n"
    assert scripts[0].checksum == compute_migration_checksum(
        "-- გამარჯობა\nselect 2;\n"
    )


def test_directory_source_rejects_duplicates_and_bad_names(tmp_path: Path) -> None:
    (tmp_path / "0001_first.sql").write_text("select 1;", encoding="utf-8")
    (tmp_path / "0001_second.sql").write_text("select 1;", encoding="utf-8")

    with pytest.raises(ValidationFailedError, match="0001"):
        SqlFileMigrationSourceAdapter(tmp_path).load_scripts()

    (tmp_path / "0001_second.sql").unlink()
    (tmp_path / "2_bad.sql").write_text("select 1;", encoding="utf-8")
    with pytest.raises(ValidationFailedError, match="2_bad.sql"):
        SqlFileMigrationSourceAdapter(tmp_path).load_scripts()


def test_missing_directory_is_reported(tmp_path: Path) -> None:
    with pytest.raises(ValidationFailedError, match="does not exist"):
        SqlFileMigrationSourceAdapter(tmp_path / "missing").load_scripts()


def test_project_migrations_are_well_formed() -> None:
    scripts = SqlFileMigrationSourceAdapter(MIGRATIONS_DIRECTORY).load_scripts()

    assert [script.name for script in scripts][:2] == [
        "0001_document_collections",
        "0002_channel_and_calendar_collections",
    ]
    for script in scripts:
        lowered_sql = script.sql.lower()
        assert "begin;" not in lowered_sql
        assert "commit;" not in lowered_sql
        assert "concurrently" not in lowered_sql
