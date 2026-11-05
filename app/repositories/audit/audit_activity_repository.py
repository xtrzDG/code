from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.audit_chain_repositories import (
    AuditActivityRepoContract,
)
from app.repositories.audit.audit_chain_queries import (
    ENTITY_ID_FIELD,
    SECURITY_EVENT_FIELD,
)
from app.repositories.document_queries import (
    CREATED_AT_FIELD,
    document_position,
    field_among,
    field_equals,
    time_range,
)
from app.repositories.listing.audit_listing import (
    ACTION_FIELD,
    ACTOR_ID_FIELD,
    ENTITY_FIELD,
)
from app.schemas.constants.compliance import AuditAction, AuditSecurityEvent
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.audit_trail import (
    AdminTenantCount,
    BusinessOperationCount,
    FailedCheckCount,
    PlatformAuditFilter,
)
from app.schemas.dto.paging import KeysetSlice
from app.schemas.dto.storage_aggregates import DocumentAggregation, DocumentGroupCount
from app.schemas.dto.storage_pages import DocumentPageQuery
from app.schemas.dto.storage_queries import DocumentFieldMatch, DocumentFilter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    DocumentQueryLimit,
)
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.storage.document_lookup_fields import BUSINESS_ID_FIELD

CONTACT_ENTITY: AuditEntityName = AuditEntityName("contact")
# What an EXPORT of personal data names: one contact's data, a segment's
# members, the CSV lists with customers or staff in them (contacts,
# bookings, leads, conversations, the audit log) and the whole business
# export (started and downloaded). An invoice or receipt PDF
# (`billing_document`) is the business's own paper, not personal data.
PERSONAL_DATA_EXPORTS: tuple[AuditEntityName, ...] = (
    CONTACT_ENTITY,
    AuditEntityName("customer_segment"),
    AuditEntityName("booking"),
    AuditEntityName("lead"),
    AuditEntityName("conversation"),
    AuditEntityName("audit_log"),
    AuditEntityName("business"),
    AuditEntityName("business_export"),
)
FAILED_CHECK_EVENTS: tuple[AuditSecurityEvent, ...] = (
    AuditSecurityEvent.LOGIN_FAILED,
    AuditSecurityEvent.OTP_LOCKED,
    AuditSecurityEvent.MFA_LOCKED,
)


class AuditActivityRepository(AuditActivityRepoContract):
    """
    The audit log across businesses: the platform's own entries (those
    that name no business, in its chain or written before it, newest first
    by time over `audit_log_entries_doc_created_at_idx`, 1042) for the
    admin security log, and the last hour's operations of every business
    grouped in the database (by action and time, `audit_log_entries_
    doc_action_idx`, 1193) for the anomaly alerts.
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[AuditLogEntryDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[AuditLogEntryDocument] = (
            collection
        )

    def page_platform_entries(
        self,
        window: KeysetSlice,
        log_filter: PlatformAuditFilter,
    ) -> list[AuditLogEntryDocument]:
        matches: list[DocumentFieldMatch] = []
        if log_filter.action is not None:
            matches.append(field_equals(ACTION_FIELD, log_filter.action))

        if log_filter.security_event is not None:
            matches.append(
                field_equals(SECURITY_EVENT_FIELD, log_filter.security_event)
            )

        return self._collection.page_by(
            DocumentPageQuery(
                where=DocumentFilter(
                    matches=tuple(matches), missing=(BUSINESS_ID_FIELD,)
                ),
                sort_fields=(CREATED_AT_FIELD,),
                is_descending=True,
                after=document_position(window.after),
                limit=DocumentQueryLimit(int(window.limit)),
            )
        )

    def count_personal_data_operations(
        self, since: Microseconds
    ) -> list[BusinessOperationCount]:
        totals: dict[str, int] = {}
        for where in (
            DocumentFilter(
                matches=(field_equals(ACTION_FIELD, AuditAction.EXPORT),),
                among=(field_among(ENTITY_FIELD, PERSONAL_DATA_EXPORTS),),
            ),
            DocumentFilter(
                matches=(
                    field_equals(ACTION_FIELD, AuditAction.DELETE),
                    field_equals(ENTITY_FIELD, CONTACT_ENTITY),
                )
            ),
        ):
            for group in self._grouped(since, where, (BUSINESS_ID_FIELD,)):
                business = group.values[0]
                if business is not None:
                    totals[str(business)] = totals.get(str(business), 0) + int(
                        group.count
                    )

        return [
            BusinessOperationCount(
                business_id=BusinessId(business), operation_count=DocumentCount(count)
            )
            for business, count in sorted(totals.items())
        ]

    def count_tenants_by_admin(
        self,
        since: Microseconds,
        actions: Sequence[AuditAction],
    ) -> list[AdminTenantCount]:
        businesses: dict[str, set[str]] = {}
        for group in self._grouped(
            since,
            DocumentFilter(among=(field_among(ACTION_FIELD, actions),)),
            (ACTOR_ID_FIELD, BUSINESS_ID_FIELD),
        ):
            actor, business = group.values
            if actor is not None and business is not None:
                businesses.setdefault(str(actor), set()).add(str(business))

        return [
            AdminTenantCount(
                actor_id=UserId(actor), business_count=DocumentCount(len(touched))
            )
            for actor, touched in sorted(businesses.items())
        ]

    def count_failed_checks(self, since: Microseconds) -> list[FailedCheckCount]:
        return [
            FailedCheckCount(
                entity=AuditEntityName(str(group.values[0])),
                entity_id=AuditEntityReference(str(group.values[1])),
                failure_count=group.count,
            )
            for group in self._grouped(
                since,
                DocumentFilter(
                    matches=(field_equals(ACTION_FIELD, AuditAction.LOGIN),),
                    among=(field_among(SECURITY_EVENT_FIELD, FAILED_CHECK_EVENTS),),
                ),
                (ENTITY_FIELD, ENTITY_ID_FIELD),
            )
            if group.values[0] is not None and group.values[1] is not None
        ]

    def _grouped(
        self,
        since: Microseconds,
        where: DocumentFilter,
        group_by: tuple[DocumentFieldPath, ...],
    ) -> list[DocumentGroupCount]:
        """Entries since `since` that meet `where`, counted per group."""

        return self._collection.count_by(
            DocumentAggregation(
                where=where.model_copy(
                    update={
                        "ranges": (time_range(CREATED_AT_FIELD, starting_at=since),)
                    }
                ),
                group_by=group_by,
            )
        )
