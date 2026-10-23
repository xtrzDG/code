"""
Closing a business and deleting it (R15-ACCOUNT-DELETION, migration 1220):
the pending closure, and the deletion ledger that outlives the business.
"""

from base_pydantic_schemas import BaseDocument, PersistentDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.business_closures import (
    BusinessClosureReason,
    DeprovisionOutcome,
    DeprovisionTarget,
)
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.typings.business_closures.constrained_integers import (
    DeletedRowCount,
    DeprovisionedItemCount,
)
from app.schemas.typings.business_closures.constrained_strings import (
    DeletionCertificateDigest,
)
from app.schemas.typings.business_closures.prefixed_id import (
    BusinessClosureId,
    BusinessDeletionId,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.privacy.constrained_integers import ProcessorErasureJobCount
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.schemas.typings.users.prefixed_id import UserId


class BusinessClosureDocument(BaseDocument):
    """
    A business on its way out (collection `business_closures`, one per
    business under an id derived from it). While it exists the assistant is
    paused and the channels that were on are off (`disconnected_channel_ids`
    keep their credentials, so a cancelled closure turns them on again with
    the assistant's former `status_before`). At `delete_after` the hourly
    sweep queues the deletion (`deletion_queued_at`), which nothing stops
    any more.
    """

    id: BusinessClosureId
    business_id: BusinessId
    reason: BusinessClosureReason
    requested_by: UserId | None = None
    requested_at: Microseconds
    delete_after: Microseconds
    status_before: BusinessStatus
    disconnected_channel_ids: list[ChannelId] = Field(default_factory=list[ChannelId])
    deletion_queued_at: Microseconds | None = None


class DeprovisionRecord(PersistentDocument):
    """What the deletion switched off at one kind of provider, and how."""

    target: DeprovisionTarget
    outcome: DeprovisionOutcome
    item_count: DeprovisionedItemCount = DeprovisionedItemCount(0)


class CertificateHolder(PersistentDocument):
    """An owner of the business when it was deleted: may download its certificate."""

    user_id: UserId


class CollectionRowCount(PersistentDocument):
    """How many rows of the business one collection held (deleted or kept)."""

    collection: DocumentCollectionName
    row_count: DeletedRowCount


class BusinessDeletionDocument(BaseDocument):
    """
    The deletion ledger (collection `business_deletions`, platform-wide; it
    names the business in `deleted_business_id`, never in the business
    column, so nothing of the business it records is left in the business's
    rows). Written when a deletion starts and completed stage by stage, so a
    retried job continues where the last attempt stopped: the providers
    switched off (`deprovisioned_at`), the business's queued jobs cleared
    and the sub-processors' erasure queued (`jobs_cleared_at`), its files
    deleted (`files_erased_at`) and its rows counted (`erased_rows`, what is
    deleted; `retained_rows`, what the law keeps: the audit log and issued
    invoices) and deleted (`completed_at`, with the certificate's digest).

    The restore drill applies every entry to a restored database, and each
    one is mirrored outside the database (the backup bucket), so a restored
    backup never brings a deleted business back. Its owners at the time
    (`owners`) may download the certificate.
    """

    id: BusinessDeletionId
    deleted_business_id: BusinessId
    business_name: BusinessName
    reason: BusinessClosureReason
    requested_by: UserId | None = None
    requested_at: Microseconds
    owners: list[CertificateHolder] = Field(default_factory=list[CertificateHolder])
    started_at: Microseconds
    deprovisioned: list[DeprovisionRecord] = Field(
        default_factory=list[DeprovisionRecord]
    )
    deprovisioned_at: Microseconds | None = None
    processor_erasure_jobs: ProcessorErasureJobCount | None = None
    jobs_cleared_at: Microseconds | None = None
    erased_files: DeletedRowCount | None = None
    files_erased_at: Microseconds | None = None
    erased_rows: list[CollectionRowCount] = Field(
        default_factory=list[CollectionRowCount]
    )
    retained_rows: list[CollectionRowCount] = Field(
        default_factory=list[CollectionRowCount]
    )
    rows_counted_at: Microseconds | None = None
    completed_at: Microseconds | None = None
    certificate_digest: DeletionCertificateDigest | None = None
