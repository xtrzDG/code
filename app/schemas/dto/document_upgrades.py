"""Rewriting stored documents to the current schema version (`migrate-documents`)."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.typings.storage.booleans import IsDocumentUpgradeDryRun
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    DocumentSchemaVersionNumber,
    DocumentUpgradeBatchSize,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.schemas.typings.storage.strings import StoredDocumentKey

DEFAULT_UPGRADE_BATCH_SIZE: DocumentUpgradeBatchSize = DocumentUpgradeBatchSize(500)


class UpgradeStoredDocumentsCommand(ImmutableDTO):
    """
    Rewrite older documents of these collections (every catalog collection
    when empty) in batches; a dry run only counts them.
    """

    collection_names: list[DocumentCollectionName] = Field(
        default_factory=list[DocumentCollectionName]
    )
    batch_size: DocumentUpgradeBatchSize = DEFAULT_UPGRADE_BATCH_SIZE
    is_dry_run: IsDocumentUpgradeDryRun = False


class CollectionUpgradeRequest(ImmutableDTO):
    """One collection of an upgrade run."""

    collection_name: DocumentCollectionName
    batch_size: DocumentUpgradeBatchSize = DEFAULT_UPGRADE_BATCH_SIZE
    is_dry_run: IsDocumentUpgradeDryRun = False


class CollectionUpgradeReport(ImmutableDTO):
    """
    Outcome for one collection.

    `outdated` rows had another version than `current_version`: `upgraded`
    were rewritten (in a dry run: would be), `newer` ones were written by a
    newer release and left alone, `changed_meanwhile` were rewritten by the
    application between read and write (a later run checks them again), and
    `failed` could not be upgraded (the first keys are listed).
    """

    collection_name: DocumentCollectionName
    current_version: DocumentSchemaVersionNumber
    outdated: DocumentCount = DocumentCount(0)
    upgraded: DocumentCount = DocumentCount(0)
    newer: DocumentCount = DocumentCount(0)
    changed_meanwhile: DocumentCount = DocumentCount(0)
    failed: DocumentCount = DocumentCount(0)
    failed_document_keys: list[StoredDocumentKey] = Field(
        default_factory=list[StoredDocumentKey]
    )


class StoredDocumentsUpgradeReport(ImmutableDTO):
    """Outcome of an upgrade run, one report per collection in run order."""

    is_dry_run: IsDocumentUpgradeDryRun = False
    collections: list[CollectionUpgradeReport] = Field(
        default_factory=list[CollectionUpgradeReport]
    )
