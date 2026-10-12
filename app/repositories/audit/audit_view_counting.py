"""
Repeated identical views, counted beside the audit log's chain.

A VIEW identical to one written in the last 5 minutes (same business,
person, entity, record and address) adds no entry: the count of the first
one goes up in `audit_view_counts`, under that entry's id. The chained
entry itself never changes, so its hash still holds.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
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
)
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.audit_chain import AuditViewCountDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import AuditViewCount
from app.schemas.typings.compliance.prefixed_id import AuditLogEntryId

# Identical views within this window are one entry with a count.
VIEW_REPEAT_WINDOW_MICROSECONDS: int = 5 * 60 * 1_000_000


class AuditViewCounting:
    """Counts a repeated view on the first one's count document."""

    def __init__(
        self,
        entries: DocumentCollectionAdapterContract[AuditLogEntryDocument],
        counts: DocumentCollectionAdapterContract[AuditViewCountDocument],
    ) -> None:
        self._entries: DocumentCollectionAdapterContract[AuditLogEntryDocument] = (
            entries
        )
        self._counts: DocumentCollectionAdapterContract[AuditViewCountDocument] = counts

    def count_if_repeated(self, entry: AuditLogEntryDocument) -> bool:
        """
        Count a VIEW on an identical one of the last 5 minutes; False when
        there is none (the view is an entry of its own).
        """

        if (
            entry.action is not AuditAction.VIEW
            or entry.business_id is None
            or entry.actor_id is None
        ):
            return False

        since = Microseconds(int(entry.created_at) - VIEW_REPEAT_WINDOW_MICROSECONDS)
        recent: list[AuditLogEntryDocument] = self._entries.list_by_range(
            time_range(CREATED_AT_FIELD, starting_at=since),
            (
                of_business(entry.business_id),
                field_equals(ACTION_FIELD, AuditAction.VIEW),
                field_equals(ENTITY_FIELD, entry.entity),
                field_equals(ACTOR_ID_FIELD, entry.actor_id),
            ),
            is_descending=True,
        )
        first: AuditLogEntryDocument | None = next(
            (stored for stored in recent if is_same_view(stored, entry)), None
        )
        if first is None:
            return False

        self._raise_count(first, entry.business_id, entry.created_at)
        return True

    def counts_of(
        self,
        business_id: BusinessId,
        entry_ids: Sequence[AuditLogEntryId],
    ) -> dict[AuditLogEntryId, AuditViewCount]:
        """The view counts of these entries (one read); absent ones count 1."""

        if not entry_ids:
            return {}

        return {
            stored.id: stored.view_count
            for stored in self._counts.get_many(
                [str(entry_id) for entry_id in entry_ids]
            )
            if stored.business_id == business_id
        }

    def _raise_count(
        self,
        first: AuditLogEntryDocument,
        business_id: BusinessId,
        now: Microseconds,
    ) -> None:
        """One more view; a parallel first repeat of the same view retries."""

        def one_more(stored: AuditViewCountDocument) -> AuditViewCountDocument:
            return stored.model_copy(
                update={
                    "view_count": AuditViewCount(int(stored.view_count) + 1),
                    "last_viewed_at": now,
                    "updated_at": now,
                }
            )

        key: str = str(first.id)
        if self._counts.modify(key, one_more) is not None:
            return

        inserted: bool = self._counts.insert_if_absent(
            key,
            AuditViewCountDocument(
                id=first.id,
                business_id=business_id,
                # An entry from before the chain may hold its count still.
                view_count=AuditViewCount(int(first.record_count or 1) + 1),
                last_viewed_at=now,
                created_at=now,
                updated_at=now,
            ),
        )
        if not inserted:
            self._counts.modify(key, one_more)


def is_same_view(stored: AuditLogEntryDocument, entry: AuditLogEntryDocument) -> bool:
    return (
        stored.entity_id == entry.entity_id
        and stored.ip_address == entry.ip_address
        and stored.actor_id == entry.actor_id
    )
