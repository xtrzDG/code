from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.contact_activity_repositories import (
    ContactActivityRepoContract,
)
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.contacts import (
    ContactActivityTotals,
    ContactListQuery,
    ContactPage,
)
from app.schemas.exceptions.application_errors import InvalidPhoneNumberError
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.contacts.constrained_strings import ContactSearchText
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.use_cases.shared.contact_search_scan import (
    ContactSearchPage,
    search_contacts,
)
from app.use_cases.shared.contact_summaries import summarize_contact_row
from app.utilities.paging.keyset_paging import finish_page, read_slice


class ListContactsUseCase(UseCaseContract[ContactListQuery, ContactPage]):
    """
    Owner finds customers to answer their data requests (export, erasure).

    Customers come most recently active first (`last_seen_at`, a keyset
    page in the database), with their channels and the number of
    conversations, bookings and leads the database counts for the page.
    Contacts made only by the owner's test chats or the autotests are never
    listed; erased customers stay, marked erased. A search shows the exact
    matches first (id, full phone, exact name: indexed) and then partial
    ones from a bounded walk of the list (`contact_list_search`); a phone
    typed in the business country's national format ("0599 12 34 56") is
    read with that country as a hint. Reading the list is personal data, so
    it is audited (VIEW of "contact").
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        contact_repo: ContactRepoContract,
        contact_activity_repo: ContactActivityRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
        phone_number_parser: PhoneNumberParserContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._contact_repo: ContactRepoContract = contact_repo
        self._contact_activity_repo: ContactActivityRepoContract = contact_activity_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser

    def run(self, input_data: ContactListQuery) -> ContactPage:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        contacts, next_cursor = self._read_page(business, input_data)
        totals: dict[ContactId, ContactActivityTotals] = (
            self._contact_activity_repo.count_for_contacts(
                business.id, [contact.id for contact in contacts]
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.VIEW,
                entity=AuditEntityName("contact"),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return ContactPage(
            items=[
                summarize_contact_row(contact, totals.get(contact.id))
                for contact in contacts
            ],
            next_cursor=next_cursor,
        )

    def _read_page(
        self,
        business: BusinessDocument,
        input_data: ContactListQuery,
    ) -> tuple[list[ContactDocument], PageCursor | None]:
        """
        Raises:
            ValidationFailedError: the cursor is broken.
        """

        search: ContactSearchText | None = input_data.search
        if search is not None and str(search).strip() != "":
            found: ContactSearchPage = search_contacts(
                self._contact_repo,
                business.id,
                search,
                self._parse_search_phone(search, business.country_code),
                input_data.page,
            )
            return found.contacts, found.next_cursor

        return finish_page(
            self._contact_repo.page_by_last_seen(
                business.id, read_slice(input_data.page)
            ),
            input_data.page,
            sort_key=lambda contact: int(contact.last_seen_at or 0),
            item_id=lambda contact: str(contact.id),
        )

    def _parse_search_phone(
        self,
        search: ContactSearchText,
        country_code: CountryCode,
    ) -> E164PhoneNumber | None:
        """The search as a full phone number, or None when it is not one."""

        try:
            return self._phone_number_parser.parse(
                RawPhoneNumberInput(str(search)), country_code
            ).e164
        except InvalidPhoneNumberError:
            return None
