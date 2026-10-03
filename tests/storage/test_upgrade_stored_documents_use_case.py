"""Which collections a document upgrade run walks, and what it reports."""

import pytest

from app.schemas.dto.document_upgrades import (
    CollectionUpgradeReport,
    CollectionUpgradeRequest,
    UpgradeStoredDocumentsCommand,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    DocumentSchemaVersionNumber,
    DocumentUpgradeBatchSize,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.use_cases.maintenance.upgrade_stored_documents_use_case import (
    UpgradeStoredDocumentsUseCase,
)
from app.utilities.storage.document_collection_catalog import DOCUMENT_COLLECTIONS


class RecordingDocumentUpgrades:
    """Fake upgrade adapter: one outdated, upgraded document per collection."""

    def __init__(self) -> None:
        self.requests: list[CollectionUpgradeRequest] = []

    def upgrade_collection(
        self,
        request: CollectionUpgradeRequest,
    ) -> CollectionUpgradeReport:
        self.requests.append(request)
        return CollectionUpgradeReport(
            collection_name=request.collection_name,
            current_version=DocumentSchemaVersionNumber(1),
            outdated=DocumentCount(1),
            upgraded=DocumentCount(1),
        )


def test_without_names_every_catalog_collection_runs_in_order() -> None:
    upgrades = RecordingDocumentUpgrades()

    report = UpgradeStoredDocumentsUseCase(upgrades).run(
        UpgradeStoredDocumentsCommand(is_dry_run=True)
    )

    assert [request.collection_name for request in upgrades.requests] == [
        definition.name for definition in DOCUMENT_COLLECTIONS
    ]
    assert all(request.is_dry_run for request in upgrades.requests)
    assert report.is_dry_run
    assert len(report.collections) == len(DOCUMENT_COLLECTIONS)


def test_named_collections_run_in_catalog_order_with_the_batch_size() -> None:
    upgrades = RecordingDocumentUpgrades()

    report = UpgradeStoredDocumentsUseCase(upgrades).run(
        UpgradeStoredDocumentsCommand(
            collection_names=[
                DocumentCollectionName("bookings"),
                DocumentCollectionName("users"),
            ],
            batch_size=DocumentUpgradeBatchSize(50),
        )
    )

    assert [str(request.collection_name) for request in upgrades.requests] == [
        "users",
        "bookings",
    ]
    assert {int(request.batch_size) for request in upgrades.requests} == {50}
    assert not report.is_dry_run
    assert [int(entry.upgraded) for entry in report.collections] == [1, 1]


def test_an_unknown_collection_stops_the_run_before_anything_is_written() -> None:
    upgrades = RecordingDocumentUpgrades()

    with pytest.raises(NotFoundError, match="missing_things"):
        UpgradeStoredDocumentsUseCase(upgrades).run(
            UpgradeStoredDocumentsCommand(
                collection_names=[
                    DocumentCollectionName("users"),
                    DocumentCollectionName("missing_things"),
                ]
            )
        )

    assert upgrades.requests == []
