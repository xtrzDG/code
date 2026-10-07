from typed_time_provider import Microseconds

from app.contracts.repositories.compliance_repositories import (
    AuditLogRepoContract,
    DpaAcceptanceRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import (
    CREATED_AT_FIELD,
    field_equals,
    of_business,
    time_range,
)
from app.repositories.listing.audit_listing import (
    ACTION_FIELD,
    ACTOR_ID_FIELD,
    ENTITY_FIELD,
    AuditLogListing,
)
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument, DpaAcceptanceDocument
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import AuditRecordCount

# Identical views within this window are one entry with a count.
VIEW_REPEAT_WINDOW_MICROSECONDS: int = 5 * 60 * 1_000_000


class AuditLogRepository(AuditLogListing, AuditLogRepoContract):
    """Append-only audit log; entries without a business are platform-wide."""

    def append(self, entry: AuditLogEntryDocument) -> None:
        if self._collection.get(str(entry.id)) is not None:
            raise ConflictError(f"Audit entry {entry.id} is already stored.")

        if entry.action is AuditAction.VIEW and self._count_repeated_view(entry):
            return

        self._collection.upsert(str(entry.id), entry)

    def _count_repeated_view(self, entry: AuditLogEntryDocument) -> bool:
        """Count the view on the same view of the last 5 minutes, if any."""

        if entry.business_id is None or entry.actor_id is None:
            return False

        since = Microseconds(int(entry.created_at) - VIEW_REPEAT_WINDOW_MICROSECONDS)
        recent: list[AuditLogEntryDocument] = self._collection.list_by_range(
            time_range(CREATED_AT_FIELD, starting_at=since),
            (
                of_business(entry.business_id),
                field_equals(ACTION_FIELD, AuditAction.VIEW),
                field_equals(ENTITY_FIELD, entry.entity),
                field_equals(ACTOR_ID_FIELD, entry.actor_id),
            ),
            is_descending=True,
        )
        same: AuditLogEntryDocument | None = next(
            (stored for stored in recent if is_same_view(stored, entry)), None
        )
        if same is None:
            return False

        def count(stored: AuditLogEntryDocument) -> AuditLogEntryDocument:
            views: int = int(stored.record_count or 1) + 1
            return stored.model_copy(
                update={
                    "record_count": AuditRecordCount(views),
                    "updated_at": entry.created_at,
                }
            )

        return self._collection.modify(str(same.id), count) is not None

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[AuditLogEntryDocument]:
        return sorted(
            self._collection.list_by_fields([of_business(business_id)]),
            key=lambda entry: entry.created_at,
        )


class DpaAcceptanceRepository(
    BusinessScopedRepository[DpaAcceptanceDocument],
    DpaAcceptanceRepoContract,
):
    def save(self, acceptance: DpaAcceptanceDocument) -> None:
        self._store(str(acceptance.id), acceptance)

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[DpaAcceptanceDocument]:
        return sorted(
            self._list_in_business(business_id),
            key=lambda acceptance: acceptance.accepted_at,
        )


def is_same_view(stored: AuditLogEntryDocument, entry: AuditLogEntryDocument) -> bool:
    return (
        stored.entity_id == entry.entity_id
        and stored.ip_address == entry.ip_address
        and stored.actor_id == entry.actor_id
    )
