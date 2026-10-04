"""
Rows of the contacts, conversations and audit log tables, a keyset page
at a time: contacts newest first (erased ones and the owner's test chats
left out, the list's search applied), the inbox view's conversations with
every message (one row per message), the audit log with its filters.
"""

from dataclasses import dataclass
from zoneinfo import ZoneInfo

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.inbox_repositories import (
    ConversationTeamRepoContract,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.inbox.inbox_views import InboxViewFilter
from app.schemas.dto.listing_filters import AuditLogFilter
from app.schemas.dto.paging import PageRequest
from app.schemas.dto.privacy.csv_exports import (
    CsvExportPage,
    CsvExportPageQuery,
    CsvRow,
)
from app.schemas.exceptions.application_errors import InvalidPhoneNumberError
from app.schemas.typings.contacts.constrained_strings import ContactSearchText
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.privacy.strings import CsvCellText
from app.use_cases.exports.business_rows import is_erased
from app.utilities.contacts.contact_search import matches_contact_search
from app.utilities.paging.keyset_paging import finish_page, read_slice
from app.utilities.privacy.csv_cells import (
    flag_cell,
    list_cell,
    moment_cell,
    text_cell,
)


@dataclass(frozen=True)
class ContactRows:
    contact_repo: ContactRepoContract
    phone_number_parser: PhoneNumberParserContract

    def read(
        self,
        business: BusinessDocument,
        zone: ZoneInfo,
        query: CsvExportPageQuery,
        page: PageRequest,
    ) -> CsvExportPage:
        contacts: list[ContactDocument]
        contacts, next_cursor = finish_page(
            self.contact_repo.page_by_business(business.id, read_slice(page)),
            page,
            sort_key=lambda contact: int(contact.created_at),
            item_id=lambda contact: str(contact.id),
        )
        search: ContactSearchText | None = query.filters.search
        search_phone: E164PhoneNumber | None = self._parse_phone(
            search, business.country_code
        )
        return CsvExportPage(
            rows=[
                contact_row(contact, zone)
                for contact in contacts
                if not is_erased(contact)
                and not is_test_only(contact)
                and matches_contact_search(contact, search, search_phone)
            ],
            next_cursor=next_cursor,
        )

    def _parse_phone(
        self, search: ContactSearchText | None, country_code: CountryCode
    ) -> E164PhoneNumber | None:
        if search is None:
            return None

        try:
            return self.phone_number_parser.parse(
                RawPhoneNumberInput(str(search)), country_code
            ).e164
        except InvalidPhoneNumberError:
            return None


def is_test_only(contact: ContactDocument) -> bool:
    """A "customer" only the owner's test chat made."""

    channels: list[ChannelKind] = [
        identity.channel for identity in contact.channel_identities
    ]
    return channels != [] and all(
        channel is ChannelKind.OWNER_TEST for channel in channels
    )


def contact_row(contact: ContactDocument, zone: ZoneInfo) -> CsvRow:
    return CsvRow(
        cells=[
            text_cell(contact.id),
            text_cell(contact.name),
            text_cell(contact.verified_phone_number or contact.phone_number),
            flag_cell(contact.verified_phone_number is not None),
            text_cell(contact.language),
            list_cell(
                dict.fromkeys(
                    identity.channel
                    for identity in contact.channel_identities
                    if identity.channel is not ChannelKind.OWNER_TEST
                )
            ),
            moment_cell(contact.created_at, zone),
            list_cell(contact.opted_out_channels),
        ]
    )


@dataclass(frozen=True)
class ConversationRows:
    conversation_repo: ConversationTeamRepoContract
    contact_repo: ContactRepoContract
    message_repo: MessageRepoContract

    def read(
        self,
        business: BusinessDocument,
        zone: ZoneInfo,
        query: CsvExportPageQuery,
        page: PageRequest,
    ) -> CsvExportPage:
        conversations: list[ConversationDocument]
        conversations, next_cursor = finish_page(
            self.conversation_repo.page_inbox(
                business.id,
                read_slice(page),
                InboxViewFilter(
                    view=query.filters.view,
                    viewer=query.user_id,
                    channel=query.filters.channel,
                ),
            ),
            page,
            sort_key=lambda conversation: int(conversation.last_message_at),
            item_id=lambda conversation: str(conversation.id),
        )
        contacts: dict[ContactId, ContactDocument] = self.contact_repo.get_many(
            business.id, [conversation.contact_id for conversation in conversations]
        )
        shown: list[ConversationDocument] = [
            conversation
            for conversation in conversations
            if not is_erased(contacts.get(conversation.contact_id))
        ]
        messages: dict[ConversationId, list[MessageDocument]] = {
            conversation.id: [] for conversation in shown
        }
        for message in self.message_repo.list_by_conversations(
            business.id, list(messages)
        ):
            messages[message.conversation_id].append(message)

        rows: list[CsvRow] = []
        for conversation in shown:
            contact: ContactDocument | None = contacts.get(conversation.contact_id)
            lead_cells: list[CsvCellText] = [
                text_cell(conversation.id),
                text_cell(conversation.channel),
                text_cell(conversation.status),
                text_cell(None if contact is None else contact.name),
                text_cell(None if contact is None else contact.phone_number),
                moment_cell(conversation.created_at, zone),
            ]
            listed: list[MessageDocument | None] = [*messages[conversation.id]]
            for row_message in listed or [None]:
                rows.append(
                    CsvRow(cells=[*lead_cells, *message_cells(row_message, zone)])
                )

        return CsvExportPage(rows=rows, next_cursor=next_cursor)


def message_cells(message: MessageDocument | None, zone: ZoneInfo) -> list[CsvCellText]:
    if message is None:
        return [text_cell(None), text_cell(None), text_cell(None)]

    return [
        moment_cell(message.created_at, zone),
        text_cell(message.author),
        text_cell(message.text),
    ]


@dataclass(frozen=True)
class AuditRows:
    audit_log_repo: AuditLogRepoContract

    def read(
        self,
        business: BusinessDocument,
        zone: ZoneInfo,
        query: CsvExportPageQuery,
        page: PageRequest,
    ) -> CsvExportPage:
        entries: list[AuditLogEntryDocument]
        entries, next_cursor = finish_page(
            self.audit_log_repo.page_by_business(
                business.id,
                read_slice(page),
                AuditLogFilter(
                    action=query.filters.action,
                    entity=query.filters.entity,
                    actor_id=query.filters.actor_id,
                    since=query.filters.since,
                    until=query.filters.until,
                ),
            ),
            page,
            sort_key=lambda entry: int(entry.created_at),
            item_id=lambda entry: str(entry.id),
        )
        return CsvExportPage(
            rows=[
                CsvRow(
                    cells=[
                        moment_cell(entry.created_at, zone),
                        text_cell(entry.action),
                        text_cell(entry.entity),
                        text_cell(entry.entity_id),
                        text_cell(entry.actor_id),
                        text_cell(entry.ip_address),
                    ]
                )
                for entry in entries
            ],
            next_cursor=next_cursor,
        )
