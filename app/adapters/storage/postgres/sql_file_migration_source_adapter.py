from pathlib import Path

from app.contracts.storage import SchemaMigrationSourceAdapterContract
from app.schemas.dto.storage import SchemaMigrationScript
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.storage.constrained_strings import SchemaMigrationName
from app.schemas.typings.storage.strings import SchemaMigrationSql
from app.utilities.storage.schema_migration_files import (
    MIGRATION_FILE_SUFFIX,
    compute_migration_checksum,
    find_duplicate_versions,
    has_no_transaction_header,
    migration_name_from_file_name,
    normalize_migration_sql,
)

# The `migrations/` directory of this build (the image copies it next to app/).
BUILD_MIGRATIONS_DIRECTORY: Path = Path(__file__).resolve().parents[4] / "migrations"


class SqlFileMigrationSourceAdapter(SchemaMigrationSourceAdapterContract):
    """
    Migration scripts read from `NNNN_slug.sql` files in one directory.

    Other files (README.md) are ignored; a misnamed `.sql` file or two files
    with the same version stop the run. Files are read as UTF-8 and their
    line endings normalized before hashing and execution. A file headed
    `-- workshop:no-transaction` is marked to run outside a transaction.
    """

    def __init__(self, migrations_directory: Path) -> None:
        self._migrations_directory: Path = migrations_directory

    def load_scripts(self) -> list[SchemaMigrationScript]:
        if not self._migrations_directory.is_dir():
            raise ValidationFailedError(
                f"Migrations directory {str(self._migrations_directory)!r} "
                "does not exist."
            )

        scripts: list[SchemaMigrationScript] = []
        for file_path in sorted(self._migrations_directory.iterdir()):
            if not file_path.is_file() or file_path.suffix != MIGRATION_FILE_SUFFIX:
                continue

            migration_name: SchemaMigrationName = migration_name_from_file_name(
                file_path.name
            )
            sql_text: str = file_path.read_text(encoding="utf-8")
            scripts.append(
                SchemaMigrationScript(
                    name=migration_name,
                    checksum=compute_migration_checksum(sql_text),
                    sql=SchemaMigrationSql(normalize_migration_sql(sql_text)),
                    is_transactional=not has_no_transaction_header(sql_text),
                )
            )

        duplicate_versions: list[str] = find_duplicate_versions(
            script.name for script in scripts
        )
        if duplicate_versions:
            raise ValidationFailedError(
                "Several migration files share a version: "
                f"{', '.join(duplicate_versions)}."
            )

        return sorted(scripts, key=lambda script: str(script.name))
