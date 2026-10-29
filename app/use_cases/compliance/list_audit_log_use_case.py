from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.compliance import AuditLogEntryView, AuditLogPage, AuditLogQuery
from app.schemas.dto.listing_filters import AuditLogFilter
from app.schemas.typings.compliance.constrained_integers import (
    AuditRecordCount,
    AuditViewCount,
)
from app.schemas.typings.compliance.prefixed_id import AuditLogEntryId
from app.schemas.typings.compliance.strings import AuditEntityName
from app.utilities.paging.keyset_paging import finish_page, read_slice


class ListAuditLogUseCase(UseCaseContract[AuditLogQuery, AuditLogPage]):
    """
    Owner reads the operations on personal data of the business, newest
    first (operations of the same microsecond the latest written first), one
    keyset page at a time, filtered by operation, entity type, person and
    period before paging. The page also names every entity type and person
    in the log, for the filters (grouped by the database). A VIEW shows how
    many identical views it stands for (`record_count`, read beside the
    chain in one read).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        audit_log_repo: AuditLogRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo

    def run(self, input_data: AuditLogQuery) -> AuditLogPage:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        entries: list[AuditLogEntryDocument]
        entries, next_cursor = finish_page(
            self._audit_log_repo.page_by_business(
                business.id,
                read_slice(input_data.page),
                AuditLogFilter(
                    action=input_data.action,
                    entity=input_data.entity,
                    actor_id=input_data.actor_id,
                    since=input_data.since,
                    until=input_data.until,
                ),
            ),
            input_data.page,
            sort_key=lambda entry: int(entry.created_at),
            item_id=lambda entry: str(entry.id),
        )
        views: dict[AuditLogEntryId, AuditViewCount] = self._audit_log_repo.view_counts(
            business.id,
            [entry.id for entry in entries if entry.action is AuditAction.VIEW],
        )
        return AuditLogPage(
            items=[view_entry(entry, views.get(entry.id)) for entry in entries],
            next_cursor=next_cursor,
            entities=self._audit_log_repo.list_entities(business.id),
            actor_ids=self._audit_log_repo.list_actors(business.id),
        )


def view_entry(
    entry: AuditLogEntryDocument, view_count: AuditViewCount | None = None
) -> AuditLogEntryView:
    """The entry as listed; a repeated view counts its views."""

    return AuditLogEntryView(
        id=entry.id,
        action=entry.action,
        entity=AuditEntityName(str(entry.entity)),
        entity_id=entry.entity_id,
        actor_id=entry.actor_id,
        ip_address=entry.ip_address,
        occurred_at=entry.created_at,
        record_count=(
            entry.record_count
            if view_count is None
            else AuditRecordCount(int(view_count))
        ),
    )
