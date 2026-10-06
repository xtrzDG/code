from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.contracts.repositories.waitlist_repositories import WaitlistEntryRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.waitlist import WaitlistListFilter, WaitlistStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.waitlist import WaitlistEntryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.growth.waitlist_views import WaitlistEntryPage, WaitlistPageQuery
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.use_cases.shared.operations_support import build_audit_entry
from app.use_cases.waitlist.waitlist_entry_views import build_entry_view
from app.utilities.paging.keyset_paging import finish_page, read_slice
from app.utilities.scheduling.zoned_time import load_time_zone

WAITLIST_ENTRY_ENTITY: AuditEntityName = AuditEntityName("waitlist_entry")
FILTER_STATUSES: dict[WaitlistListFilter, tuple[WaitlistStatus, ...]] = {
    WaitlistListFilter.ACTIVE: (WaitlistStatus.WAITING, WaitlistStatus.OFFERED),
    WaitlistListFilter.BOOKED: (WaitlistStatus.BOOKED,),
    WaitlistListFilter.ENDED: (WaitlistStatus.EXPIRED,),
}


class ListWaitlistUseCase(UseCaseContract[WaitlistPageQuery, WaitlistEntryPage]):
    """
    Bookings → Waitlist, one keyset page at a time: the customers still
    waiting or offered a place (first come first, the order places are
    offered in), the booked ones or the ended ones (the latest first), with
    the offered place in the business's time, the resource and the service.
    Owners and staff; customers' names are personal data, so the view is
    audited. Test chats' entries are left out.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        waitlist_entry_repo: WaitlistEntryRepoContract,
        contact_repo: ContactRepoContract,
        resource_repo: ResourceRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._entry_repo: WaitlistEntryRepoContract = waitlist_entry_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: WaitlistPageQuery) -> WaitlistEntryPage:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        is_open: bool = input_data.list_filter is WaitlistListFilter.ACTIVE
        fetched: list[WaitlistEntryDocument] = self._entry_repo.page_in_statuses(
            business.id,
            FILTER_STATUSES[input_data.list_filter],
            read_slice(input_data.page),
            is_descending=not is_open,
        )
        items, next_cursor = finish_page(
            fetched,
            input_data.page,
            sort_key=lambda entry: int(entry.created_at),
            item_id=lambda entry: str(entry.id),
        )
        contacts = self._contact_repo.get_many(
            business.id, list({entry.contact_id for entry in items})
        )
        service_ids: list[KnowledgeItemId] = list(
            {
                entry.service_item_id
                for entry in items
                if entry.service_item_id is not None
            }
        )
        titles = (
            self._knowledge_item_repo.get_many(business.id, service_ids)
            if service_ids
            else {}
        )
        resources = {
            resource.id: resource
            for resource in self._resource_repo.list_by_business(business.id)
        }
        now: Microseconds = self._wall_clock.now_unix()
        self._audit_log_repo.append(
            build_audit_entry(
                business.id,
                input_data.user_id,
                AuditAction.VIEW,
                WAITLIST_ENTRY_ENTITY,
                None,
                now,
                input_data.client_ip_address,
            )
        )
        zone = load_time_zone(business.timezone)
        return WaitlistEntryPage(
            items=[
                build_entry_view(entry, contacts, resources, titles, zone)
                for entry in items
            ],
            next_cursor=next_cursor,
            timezone=business.timezone,
        )
