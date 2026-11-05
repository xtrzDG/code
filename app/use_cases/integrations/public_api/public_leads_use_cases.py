"""The public API's leads: `GET /v1/public-api/leads[/{id}]`."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.integrations import PublicRecordReaderContract
from app.contracts.repositories.booking_repositories import LeadRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.integrations import ApiKeyScope
from app.schemas.dto.public_api.access import PublicLeadQuery, PublicListQuery
from app.schemas.dto.public_api.pages import PublicLeadPage
from app.schemas.dto.public_api.records import PublicLead
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.bookings.booleans import IsSandboxIncluded
from app.use_cases.integrations.api_key_records import require_scope
from app.use_cases.integrations.public_api.public_access import (
    API_LEAD_ENTITY,
    key_business,
    record_public_read,
)
from app.utilities.paging.keyset_paging import finish_page, read_slice

UNKNOWN_LEAD_MESSAGE: str = "Lead not found."


class ListPublicLeadsUseCase(UseCaseContract[PublicListQuery, PublicLeadPage]):
    """
    The key's business's leads, the newest first, one keyset page at a
    time (test leads left out). Needs `leads:read`; audited.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        lead_repo: LeadRepoContract,
        record_reader: PublicRecordReaderContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._lead_repo: LeadRepoContract = lead_repo
        self._record_reader: PublicRecordReaderContract = record_reader
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PublicListQuery) -> PublicLeadPage:
        require_scope(input_data.principal, ApiKeyScope.LEADS_READ)
        business = key_business(self._business_repo, input_data.principal)
        leads, next_cursor = finish_page(
            self._lead_repo.page_by_business(
                business.id,
                read_slice(input_data.page),
                None,
                IsSandboxIncluded(False),
            ),
            input_data.page,
            lambda lead: int(lead.created_at),
            lambda lead: str(lead.id),
        )
        items = self._record_reader.leads(business, leads)
        record_public_read(
            self._audit_log_repo,
            input_data.principal,
            API_LEAD_ENTITY,
            len(items),
            self._wall_clock.now_unix(),
        )
        return PublicLeadPage(items=items, next_cursor=next_cursor)


class GetPublicLeadUseCase(UseCaseContract[PublicLeadQuery, PublicLead]):
    """
    One lead of the key's business (404 otherwise). Needs `leads:read`;
    audited unless it answers the lead the key has just made.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        record_reader: PublicRecordReaderContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
        is_audited: bool = True,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._record_reader: PublicRecordReaderContract = record_reader
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._is_audited: bool = is_audited

    def run(self, input_data: PublicLeadQuery) -> PublicLead:
        if self._is_audited:
            require_scope(input_data.principal, ApiKeyScope.LEADS_READ)
        business = key_business(self._business_repo, input_data.principal)
        lead = self._record_reader.lead(business, input_data.lead_id)
        if lead is None:
            raise NotFoundError(UNKNOWN_LEAD_MESSAGE)

        if self._is_audited:
            record_public_read(
                self._audit_log_repo,
                input_data.principal,
                API_LEAD_ENTITY,
                1,
                self._wall_clock.now_unix(),
            )
        return lead
