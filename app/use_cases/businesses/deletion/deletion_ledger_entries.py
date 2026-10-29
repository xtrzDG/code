"""The deletion ledger's entry of a business, as the deletion fills it."""

from typed_time_provider import Microseconds

from app.contracts.repositories.business_closure_repositories import (
    BusinessDeletionChange,
)
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.business_closures import (
    BusinessClosureDocument,
    BusinessDeletionDocument,
    CertificateHolder,
    CollectionRowCount,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.business_closures.business_rows import BusinessTableRows
from app.schemas.typings.business_closures.constrained_integers import (
    DeletedRowCount,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.business_closures.closure_identity import deletion_id_for
from app.utilities.business_closures.retained_tables import (
    is_retained,
    outlives_deletion,
)


def new_ledger_entry(
    business: BusinessDocument,
    closure: BusinessClosureDocument,
    now: Microseconds,
) -> BusinessDeletionDocument:
    """
    The entry of a deletion that starts: the business's name and id, why
    and by whom it was closed, and who may download the certificate (its
    owners now, and whoever closed it).
    """

    owners: list[UserId] = [
        member.user_id
        for member in business.members
        if member.role is BusinessMemberRole.OWNER
    ]
    if closure.requested_by is not None:
        owners.append(closure.requested_by)

    return BusinessDeletionDocument(
        id=deletion_id_for(business.id),
        deleted_business_id=business.id,
        business_name=business.name,
        reason=closure.reason,
        requested_by=closure.requested_by,
        requested_at=closure.requested_at,
        owners=[
            CertificateHolder(user_id=user_id) for user_id in dict.fromkeys(owners)
        ],
        started_at=now,
        created_at=now,
        updated_at=now,
    )


def erasable_tables(counts: list[BusinessTableRows]) -> list[BusinessTableRows]:
    """
    The tables whose rows of the business go now: all but the retained ones
    and the queue (the sub-processors' erasure jobs of this deletion wait
    there for their turn; finished jobs are purged like every other).
    """

    return [count for count in counts if not outlives_deletion(count.table)]


def row_counts(counts: list[BusinessTableRows]) -> list[CollectionRowCount]:
    return [
        CollectionRowCount(
            collection=count.table, row_count=DeletedRowCount(int(count.row_count))
        )
        for count in counts
    ]


def retained_counts(counts: list[BusinessTableRows]) -> list[CollectionRowCount]:
    return row_counts([count for count in counts if is_retained(count.table)])


def stage_change(**results: object) -> BusinessDeletionChange:
    """
    The ledger change of one finished stage: its results and the moment
    (`updated_at`) set on the entry as stored now (each assignment is
    validated, the documents validate assignments).
    """

    def change(stored: BusinessDeletionDocument) -> BusinessDeletionDocument:
        for name, value in results.items():
            setattr(stored, name, value)
        return stored

    return change
