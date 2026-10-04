from typing import Protocol
from zoneinfo import ZoneInfo

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.repositories.booking_repositories import (
    BookingRepoContract,
    LeadRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.inbox_repositories import (
    ConversationTeamRepoContract,
)
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import BusinessAccessMode
from app.schemas.constants.privacy import CsvExportKind
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.paging import PageRequest
from app.schemas.dto.privacy.csv_exports import CsvExportPage, CsvExportPageQuery
from app.schemas.typings.platform.constrained_integers import PageSize
from app.use_cases.exports.business_rows import BookingRows, LeadRows
from app.use_cases.exports.people_rows import AuditRows, ContactRows, ConversationRows
from app.utilities.scheduling.zoned_time import load_time_zone

# Rows read per page: the largest list page; conversations bring every
# message along, so fewer of them at a time.
PAGE_SIZES: dict[CsvExportKind, PageSize] = {
    CsvExportKind.BOOKINGS: PageSize(200),
    CsvExportKind.LEADS: PageSize(200),
    CsvExportKind.CONTACTS: PageSize(200),
    CsvExportKind.CONVERSATIONS: PageSize(25),
    CsvExportKind.AUDIT_LOG: PageSize(200),
}


class CsvRowReader(Protocol):
    def read(
        self,
        business: BusinessDocument,
        zone: ZoneInfo,
        query: CsvExportPageQuery,
        page: PageRequest,
    ) -> CsvExportPage: ...


class ReadCsvExportPageUseCase(UseCaseContract[CsvExportPageQuery, CsvExportPage]):
    """
    One page of the rows of a CSV export the owner started
    (StartCsvExportUseCase): the same keyset page, filters and order as the
    table's list in the cabinet, cells formatted for a spreadsheet in the
    business's time zone, records of erased customers left out. Each page
    checks the owner again, so a stream outliving a role change stops.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        booking_repo: BookingRepoContract,
        resource_repo: ResourceRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        lead_repo: LeadRepoContract,
        contact_repo: ContactRepoContract,
        conversation_repo: ConversationTeamRepoContract,
        message_repo: MessageRepoContract,
        audit_log_repo: AuditLogRepoContract,
        phone_number_parser: PhoneNumberParserContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._readers: dict[CsvExportKind, CsvRowReader] = {
            CsvExportKind.BOOKINGS: BookingRows(
                booking_repo, resource_repo, knowledge_item_repo, contact_repo
            ),
            CsvExportKind.LEADS: LeadRows(lead_repo, contact_repo),
            CsvExportKind.CONTACTS: ContactRows(contact_repo, phone_number_parser),
            CsvExportKind.CONVERSATIONS: ConversationRows(
                conversation_repo, contact_repo, message_repo
            ),
            CsvExportKind.AUDIT_LOG: AuditRows(audit_log_repo),
        }

    def run(self, input_data: CsvExportPageQuery) -> CsvExportPage:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
                access_mode=BusinessAccessMode.WRITE,
            )
        )
        return self._readers[input_data.kind].read(
            business,
            load_time_zone(business.timezone),
            input_data,
            PageRequest(size=PAGE_SIZES[input_data.kind], cursor=input_data.cursor),
        )
