from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.repositories import (
    AuditLogRepoContract,
    BookingRepoContract,
    ContactRepoContract,
    ConversationRepoContract,
    LeadRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.contacts import (
    ContactActivity,
    ContactListQuery,
    ContactPage,
    ContactSummaryView,
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
from app.use_cases.contacts.contact_summaries import (
    collect_contact_activity,
    is_test_contact,
    summarize_contact,
)
from app.utilities.contacts.contact_search import matches_contact_search
from app.utilities.paging.cursor_paging import take_page


class ListContactsUseCase(UseCaseContract[ContactListQuery, ContactPage]):
    """
    Owner finds customers to answer their data requests (export, erasure).

    Customers come most recently active first, with their channels and the
    number of conversations, bookings and leads. Customers made only by the
    owner's test chats or the autotests are left out; erased customers stay
    in the list, marked erased. The search runs before paging; a phone typed
    in the business country's national format ("0599 12 34 56") is read
    with that country as a hint. Reading the list is personal data, so it is
    audited (VIEW of "contact").
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        contact_repo: ContactRepoContract,
        conversation_repo: ConversationRepoContract,
        booking_repo: BookingRepoContract,
        lead_repo: LeadRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
        phone_number_parser: PhoneNumberParserContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._contact_repo: ContactRepoContract = contact_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._lead_repo: LeadRepoContract = lead_repo
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
        activity: dict[ContactId, ContactActivity] = collect_contact_activity(
            business.id,
            self._conversation_repo,
            self._booking_repo,
            self._lead_repo,
        )
        search_phone: E164PhoneNumber | None = self._parse_search_phone(
            input_data.search, business.country_code
        )
        summaries: list[ContactSummaryView] = []
        for contact in self._contact_repo.list_by_business(business.id):
            contact_activity: ContactActivity = activity.get(
                contact.id, ContactActivity()
            )
            if is_test_contact(contact, contact_activity):
                continue

            if matches_contact_search(contact, input_data.search, search_phone):
                summaries.append(summarize_contact(contact, contact_activity))

        items, next_cursor = take_page(
            summaries,
            input_data.page,
            sort_key=lambda summary: int(summary.last_activity_at),
            item_id=lambda summary: str(summary.id),
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
        return ContactPage(items=items, next_cursor=next_cursor)

    def _parse_search_phone(
        self,
        search: ContactSearchText | None,
        country_code: CountryCode,
    ) -> E164PhoneNumber | None:
        """The search as a full phone number, or None when it is not one."""

        if search is None:
            return None

        try:
            return self._phone_number_parser.parse(
                RawPhoneNumberInput(str(search)), country_code
            ).e164
        except InvalidPhoneNumberError:
            return None
