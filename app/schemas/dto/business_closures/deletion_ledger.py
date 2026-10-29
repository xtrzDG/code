"""The deletion ledger's copy outside the database (the backup bucket)."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.typings.business_closures.prefixed_id import BusinessDeletionId
from app.schemas.typings.businesses.prefixed_id import BusinessId


class DeletionLedgerRecord(ImmutableDTO):
    """
    One deleted business, as the restore drill needs it: which business,
    under which ledger entry, since when. Nothing personal.
    """

    business_id: BusinessId
    deletion_id: BusinessDeletionId
    started_at: Microseconds
