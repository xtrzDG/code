"""Pages of the audit log and the choices of its filters."""

from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import (
    CREATED_AT_FIELD,
    field_equals,
    time_range,
)
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.listing_filters import AuditLogFilter
from app.schemas.dto.paging import KeysetSlice
from app.schemas.dto.storage_aggregates import DocumentAggregation
from app.schemas.dto.storage_queries import (
    DocumentFieldMatch,
    DocumentFieldRange,
    DocumentFilter,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.users.prefixed_id import UserId

ACTOR_ID_FIELD: DocumentFieldPath = DocumentFieldPath("actor_id")
ACTION_FIELD: DocumentFieldPath = DocumentFieldPath("action")
ENTITY_FIELD: DocumentFieldPath = DocumentFieldPath("entity")


class AuditLogListing(BusinessScopedRepository[AuditLogEntryDocument]):
    """
    A business's audit entries newest first (entries of the same
    microsecond by id), filtered by operation, entity type, person and
    period; the entity types and persons present, for the filters.
    """

    def page_by_business(
        self,
        business_id: BusinessId,
        window: KeysetSlice,
        log_filter: AuditLogFilter,
    ) -> list[AuditLogEntryDocument]:
        matches: list[DocumentFieldMatch] = []
        if log_filter.action is not None:
            matches.append(field_equals(ACTION_FIELD, log_filter.action))

        if log_filter.entity is not None:
            matches.append(field_equals(ENTITY_FIELD, log_filter.entity))

        if log_filter.actor_id is not None:
            matches.append(field_equals(ACTOR_ID_FIELD, log_filter.actor_id))

        ranges: tuple[DocumentFieldRange, ...] = ()
        if log_filter.since is not None or log_filter.until is not None:
            ranges = (
                time_range(
                    CREATED_AT_FIELD,
                    starting_at=log_filter.since,
                    ending_before=log_filter.until,
                ),
            )

        return self._page_in_business(
            business_id,
            (CREATED_AT_FIELD,),
            window,
            DocumentFilter(matches=tuple(matches), ranges=ranges),
        )

    def list_entities(self, business_id: BusinessId) -> list[AuditEntityName]:
        """Every entity type in the business's log, by name."""

        return sorted(
            (
                AuditEntityName(str(group.values[0]))
                for group in self._aggregate_in_business(
                    business_id, DocumentAggregation(group_by=(ENTITY_FIELD,))
                )
                if group.values[0] is not None
            ),
            key=str,
        )

    def list_actors(self, business_id: BusinessId) -> list[UserId]:
        """Every person in the business's log, the most recent first."""

        groups = [
            group
            for group in self._aggregate_in_business(
                business_id,
                DocumentAggregation(
                    group_by=(ACTOR_ID_FIELD,), latest_of=CREATED_AT_FIELD
                ),
            )
            if group.values[0] is not None
        ]
        groups.sort(
            key=lambda group: (
                -1 if group.latest is None else int(group.latest),
                str(group.values[0]),
            ),
            reverse=True,
        )
        return [UserId(str(group.values[0])) for group in groups]
