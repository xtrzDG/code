import logging

from app.contracts.storage import StoredDocumentUpgradeAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.document_upgrades import (
    CollectionUpgradeReport,
    CollectionUpgradeRequest,
    StoredDocumentsUpgradeReport,
    UpgradeStoredDocumentsCommand,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_catalog import DOCUMENT_COLLECTIONS

LOGGER: logging.Logger = logging.getLogger(__name__)


class UpgradeStoredDocumentsUseCase(
    UseCaseContract[UpgradeStoredDocumentsCommand, StoredDocumentsUpgradeReport]
):
    """
    Rewrite stored documents of older schema versions in the current shape
    (`workshop migrate-documents`), so the upcasters of those versions can be
    retired and every row reads without an upgrade.

    Run it after a release that bumped a `schema_version` is fully deployed
    (no instance of the previous release left): rows rewritten earlier would
    be read by the previous release in a shape it may not know. Collections
    run one after another in catalog order (only the named ones, if any);
    an unknown name is a NotFoundError before anything is written. Running
    it again is harmless: current rows are never touched.
    """

    def __init__(self, document_upgrades: StoredDocumentUpgradeAdapterContract) -> None:
        self._document_upgrades: StoredDocumentUpgradeAdapterContract = (
            document_upgrades
        )

    def run(
        self,
        input_data: UpgradeStoredDocumentsCommand,
    ) -> StoredDocumentsUpgradeReport:
        collection_names: list[DocumentCollectionName] = select_collections(
            input_data.collection_names
        )
        reports: list[CollectionUpgradeReport] = []
        for collection_name in collection_names:
            request = CollectionUpgradeRequest(
                collection_name=collection_name,
                batch_size=input_data.batch_size,
                is_dry_run=input_data.is_dry_run,
            )
            report: CollectionUpgradeReport = (
                self._document_upgrades.upgrade_collection(request)
            )
            LOGGER.info(
                "Stored documents of %s: %s outdated, %s upgraded, %s newer, "
                "%s changed meanwhile, %s failed (dry run: %s).",
                str(collection_name),
                int(report.outdated),
                int(report.upgraded),
                int(report.newer),
                int(report.changed_meanwhile),
                int(report.failed),
                input_data.is_dry_run,
            )
            reports.append(report)

        return StoredDocumentsUpgradeReport(
            is_dry_run=input_data.is_dry_run,
            collections=reports,
        )


def select_collections(
    requested: list[DocumentCollectionName],
) -> list[DocumentCollectionName]:
    """The requested collections in catalog order; all of them when none."""

    catalog: list[DocumentCollectionName] = [
        definition.name for definition in DOCUMENT_COLLECTIONS
    ]
    unknown: list[DocumentCollectionName] = [
        name for name in requested if name not in catalog
    ]
    if unknown:
        raise NotFoundError(
            "Not document collections: "
            + ", ".join(str(name) for name in unknown)
            + "."
        )

    if not requested:
        return catalog

    return [name for name in catalog if name in requested]
