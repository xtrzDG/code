from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.contact_activity_repositories import (
    ContactActivityRepoContract,
)
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    ConversationRepoContract,
)
from app.contracts.repositories.customer_repositories import (
    CustomerHistoryRepoContract,
    CustomerSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.paging import PageRequest
from app.schemas.dto.search import BusinessSearchQuery, BusinessSearchResults
from app.schemas.exceptions.application_errors import InvalidPhoneNumberError
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.contacts.constrained_strings import ContactSearchText
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.platform.constrained_integers import PageSize
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.search.search_hits import (
    booking_hit,
    conversation_hit,
    read_booking_id,
    read_conversation_id,
    without_duplicates,
)
from app.use_cases.shared.contact_search_scan import search_contacts
from app.use_cases.shared.contact_summaries import summarize_contact_row
from app.use_cases.shared.customer_phone_privacy import (
    protect_phone,
    sees_phone_numbers,
)

# Hits of each group at most (the palette shows a few of each).
GROUP_LIMIT: int = 5
SEARCH_ENTITY: AuditEntityName = AuditEntityName("customer_search")


class SearchBusinessUseCase(
    UseCaseContract[BusinessSearchQuery, BusinessSearchResults]
):
    """
    The cabinet's search (Cmd/Ctrl+K) for owners and staff: customers by
    name, phone (any format, national too) or id, exact matches first
    (indexed) and then partial ones from a bounded walk of the customer
    list; their latest conversations and bookings (one read each); a
    conversation or booking named by its id. At most five of each group.
    Message texts are searched in the Inbox. Staff see phones masked unless
    the owner allowed them. Names and phones are personal data, so a search
    that found someone is audited (VIEW of customer_search).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        contact_repo: ContactRepoContract,
        conversation_repo: ConversationRepoContract,
        booking_repo: BookingRepoContract,
        contact_activity_repo: ContactActivityRepoContract,
        customer_history_repo: CustomerHistoryRepoContract,
        customer_settings_repo: CustomerSettingsRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
        phone_number_parser: PhoneNumberParserContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._contact_repo: ContactRepoContract = contact_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._contact_activity_repo: ContactActivityRepoContract = contact_activity_repo
        self._history_repo: CustomerHistoryRepoContract = customer_history_repo
        self._settings_repo: CustomerSettingsRepoContract = customer_settings_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser

    def run(self, input_data: BusinessSearchQuery) -> BusinessSearchResults:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        text: str = str(input_data.text).strip()
        if text == "":
            return BusinessSearchResults()

        customers: list[ContactDocument] = self._find_customers(business, text)
        ids: list[ContactId] = [contact.id for contact in customers]
        limit = DocumentQueryLimit(GROUP_LIMIT)
        conversations: list[ConversationDocument] = without_duplicates(
            [
                *self._conversation_named(business, text),
                *self._history_repo.latest_conversations_of(business.id, ids, limit),
            ]
        )[:GROUP_LIMIT]
        bookings: list[BookingDocument] = without_duplicates(
            [
                *self._booking_named(business, text),
                *self._history_repo.latest_bookings_of(business.id, ids, limit),
            ]
        )[:GROUP_LIMIT]
        named: dict[ContactId, ContactDocument] = {
            **self._contact_repo.get_many(
                business.id,
                [
                    *(item.contact_id for item in conversations),
                    *(item.contact_id for item in bookings),
                ],
            ),
            **{contact.id: contact for contact in customers},
        }
        totals = self._contact_activity_repo.count_for_contacts(business.id, ids)
        sees_phones: bool = sees_phone_numbers(
            business, input_data.user_id, self._settings_repo
        )
        if customers or conversations or bookings:
            self._audit(business, input_data)

        return BusinessSearchResults(
            customers=[
                protect_phone(
                    summarize_contact_row(contact, totals.get(contact.id)), sees_phones
                )
                for contact in customers
            ],
            conversations=[conversation_hit(item, named) for item in conversations],
            bookings=[booking_hit(item, named) for item in bookings],
        )

    def _find_customers(
        self, business: BusinessDocument, text: str
    ) -> list[ContactDocument]:
        search = ContactSearchText(text[:100])
        return search_contacts(
            self._contact_repo,
            business.id,
            search,
            self._parse_phone(text, business),
            PageRequest(size=PageSize(GROUP_LIMIT)),
        ).contacts

    def _conversation_named(
        self, business: BusinessDocument, text: str
    ) -> list[ConversationDocument]:
        conversation_id = read_conversation_id(text)
        found = (
            None
            if conversation_id is None
            else self._conversation_repo.get(business.id, conversation_id)
        )
        return [] if found is None or found.is_sandbox else [found]

    def _booking_named(
        self, business: BusinessDocument, text: str
    ) -> list[BookingDocument]:
        booking_id = read_booking_id(text)
        found = (
            None
            if booking_id is None
            else self._booking_repo.get(business.id, booking_id)
        )
        return [] if found is None or found.is_sandbox else [found]

    def _parse_phone(
        self, text: str, business: BusinessDocument
    ) -> E164PhoneNumber | None:
        try:
            return self._phone_number_parser.parse(
                RawPhoneNumberInput(text), business.country_code
            ).e164
        except InvalidPhoneNumberError:
            return None

    def _audit(self, business: BusinessDocument, query: BusinessSearchQuery) -> None:
        now: Microseconds = self._wall_clock.now_unix()
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=query.user_id,
                action=AuditAction.VIEW,
                entity=SEARCH_ENTITY,
                ip_address=query.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
