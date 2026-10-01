from app.contracts.repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.compliance import AuditLogEntryView, AuditLogPage, AuditLogQuery
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.paging.cursor_paging import take_page


class ListAuditLogUseCase(UseCaseContract[AuditLogQuery, AuditLogPage]):
    """
    Owner reads the operations on personal data of the business, newest
    first, one page at a time, filtered by operation, entity type, person
    and period before paging. The page also names every entity type and
    person in the log, for the filters.
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
        entries: list[AuditLogEntryDocument] = self._audit_log_repo.list_by_business(
            business.id
        )
        # Entries written in the same microsecond keep the order they were
        # appended in: the position breaks ties after the time.
        positions: dict[str, int] = {
            str(entry.id): position for position, entry in enumerate(entries)
        }
        selected, next_cursor = take_page(
            [entry for entry in entries if matches_filters(entry, input_data)],
            input_data.page,
            sort_key=lambda entry: int(entry.created_at),
            item_id=lambda entry: f"{positions[str(entry.id)]:012d}:{entry.id}",
        )
        return AuditLogPage(
            items=[view_entry(entry) for entry in selected],
            next_cursor=next_cursor,
            entities=sorted(
                {entry.entity for entry in entries},
                key=lambda entity: str(entity),
            ),
            actor_ids=list_actors(entries),
        )


def matches_filters(entry: AuditLogEntryDocument, query: AuditLogQuery) -> bool:
    return (
        (query.action is None or entry.action is query.action)
        and (query.entity is None or entry.entity == query.entity)
        and (query.actor_id is None or entry.actor_id == query.actor_id)
        and (query.since is None or entry.created_at >= query.since)
        and (query.until is None or entry.created_at < query.until)
    )


def list_actors(entries: list[AuditLogEntryDocument]) -> list[UserId]:
    """Every person in the log, most recent first."""

    actors: list[UserId] = []
    for entry in reversed(entries):
        if entry.actor_id is not None and entry.actor_id not in actors:
            actors.append(entry.actor_id)

    return actors


def view_entry(entry: AuditLogEntryDocument) -> AuditLogEntryView:
    return AuditLogEntryView(
        id=entry.id,
        action=entry.action,
        entity=AuditEntityName(str(entry.entity)),
        entity_id=entry.entity_id,
        actor_id=entry.actor_id,
        ip_address=entry.ip_address,
        occurred_at=entry.created_at,
    )
