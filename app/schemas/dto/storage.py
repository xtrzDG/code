from typing import Self

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field, model_validator
from typed_time_provider import Microseconds

from app.schemas.constants.storage import StorageScopeKind
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.booleans import IsMigrationDryRun
from app.schemas.typings.storage.constrained_strings import (
    SchemaMigrationChecksum,
    SchemaMigrationName,
)
from app.schemas.typings.storage.strings import SchemaMigrationSql


class StorageScope(ImmutableDTO):
    """
    Whose rows storage operations may touch.

    A BUSINESS scope carries the business id that Postgres row-level security
    compares with every row; the PLATFORM scope sees all businesses (server
    code that is not acting for one business: webhook routing, sign-in,
    admin views, background jobs that walk all businesses).
    """

    kind: StorageScopeKind
    business_id: BusinessId | None = None

    @model_validator(mode="after")
    def require_business_id_only_in_business_scope(self) -> Self:
        has_business_id: bool = self.business_id is not None
        if has_business_id != (self.kind is StorageScopeKind.BUSINESS):
            raise ValueError(
                "A business storage scope needs a business id; "
                "the platform scope must not have one."
            )

        return self

    @classmethod
    def platform_wide(cls) -> Self:
        return cls(kind=StorageScopeKind.PLATFORM)

    @classmethod
    def for_business(cls, business_id: BusinessId) -> Self:
        return cls(kind=StorageScopeKind.BUSINESS, business_id=business_id)


class SchemaMigrationScript(ImmutableDTO):
    """One migration file: name (version and slug), checksum and SQL."""

    name: SchemaMigrationName
    checksum: SchemaMigrationChecksum
    sql: SchemaMigrationSql


class AppliedSchemaMigration(ImmutableDTO):
    """A migration recorded in the database's schema_migrations table."""

    name: SchemaMigrationName
    checksum: SchemaMigrationChecksum
    applied_at: Microseconds


class ApplyDatabaseMigrationsCommand(ImmutableDTO):
    """Apply pending migrations, or only list them when `is_dry_run`."""

    is_dry_run: IsMigrationDryRun = False


class DatabaseMigrationsReport(ImmutableDTO):
    """
    Outcome of a migration run.

    `pending` is non-empty only in a dry run. `unknown_applied` lists
    migrations recorded in the database but missing from the directory (for
    example applied by a newer release); they are reported, never undone.
    """

    already_applied: list[SchemaMigrationName] = Field(
        default_factory=list[SchemaMigrationName]
    )
    newly_applied: list[SchemaMigrationName] = Field(
        default_factory=list[SchemaMigrationName]
    )
    pending: list[SchemaMigrationName] = Field(
        default_factory=list[SchemaMigrationName]
    )
    unknown_applied: list[SchemaMigrationName] = Field(
        default_factory=list[SchemaMigrationName]
    )
