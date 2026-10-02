from collections import defaultdict
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.conversation_feed.conversation_views import (
    ConversationListQuery,
    ConversationPage,
    ConversationSummaryView,
    ConversationViewSource,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.utilities.conversations.conversation_search import matches_search
from app.utilities.paging.cursor_paging import take_page
from app.utilities.scheduling.zoned_time import (
    load_time_zone,
    local_day_start_microseconds,
    parse_local_date,
)

CONVERSATION_ENTITY: AuditEntityName = AuditEntityName("conversation")


class ListConversationsUseCase(
    UseCaseContract[ConversationListQuery, ConversationPage]
):
    """
    One page of the conversation feed of a business for owners and staff
    (concept section 8, /conversations), the latest message first.

    Filters run before paging: channel, status, a period of local dates in
    the business time zone (conversations going on then: started before its
    end, last message after its start), and a search over the customer's
    name, the phone by its digits in any format, and the words of every
    message in any script. Sandbox conversations (owner test chat,
    autotests) appear only on request. Rows carry counts and a preview of
    the last message, not the messages themselves.

    The rows show customers' names, phones and messages, so every page is
    audited as a view of "conversation" (the search text is not stored: it
    may itself be personal data).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        conversation_repo: ConversationRepoContract,
        contact_repo: ContactRepoContract,
        message_repo: MessageRepoContract,
        summary_transformer: TransformerContract[
            ConversationViewSource, ConversationSummaryView
        ],
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._message_repo: MessageRepoContract = message_repo
        self._summary_transformer: TransformerContract[
            ConversationViewSource, ConversationSummaryView
        ] = summary_transformer
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ConversationListQuery) -> ConversationPage:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        period_start, period_end = self._period(business, input_data)
        candidates: list[ConversationDocument] = [
            conversation
            for conversation in self._conversation_repo.list_by_business(business.id)
            if (input_data.include_sandbox or not conversation.is_sandbox)
            and (
                input_data.channel is None or conversation.channel is input_data.channel
            )
            and (input_data.status is None or conversation.status is input_data.status)
            and (
                period_start is None
                or int(conversation.last_message_at) >= period_start
            )
            and (period_end is None or int(conversation.created_at) < period_end)
        ]
        messages_by_conversation: dict[ConversationId, list[MessageDocument]] | None = (
            None
        )
        contacts: dict[ContactId, ContactDocument] | None = None
        if input_data.search is not None:
            messages_by_conversation = self._messages_by_conversation(business)
            contacts = {
                contact.id: contact
                for contact in self._contact_repo.list_by_business(business.id)
            }
            candidates = [
                conversation
                for conversation in candidates
                if self._matches(
                    str(input_data.search),
                    conversation,
                    contacts.get(conversation.contact_id),
                    messages_by_conversation.get(conversation.id, []),
                )
            ]

        page: list[ConversationDocument]
        next_cursor: PageCursor | None
        page, next_cursor = take_page(
            candidates,
            input_data.page,
            sort_key=lambda conversation: int(conversation.last_message_at),
            item_id=lambda conversation: str(conversation.id),
        )
        now: Microseconds = self._wall_clock.now_unix()
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.VIEW,
                entity=CONVERSATION_ENTITY,
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return ConversationPage(
            items=[
                self._summary_transformer.transform(
                    ConversationViewSource(
                        conversation=conversation,
                        contact=(
                            self._contact_repo.get(business.id, conversation.contact_id)
                            if contacts is None
                            else contacts.get(conversation.contact_id)
                        ),
                        messages=(
                            self._message_repo.list_by_conversation(
                                business.id, conversation.id
                            )
                            if messages_by_conversation is None
                            else messages_by_conversation.get(conversation.id, [])
                        ),
                    )
                )
                for conversation in page
            ],
            next_cursor=next_cursor,
        )

    def _period(
        self,
        business: BusinessDocument,
        query: ConversationListQuery,
    ) -> tuple[int | None, int | None]:
        """UTC microseconds of the period's start and end (exclusive)."""

        zone: ZoneInfo = load_time_zone(business.timezone)
        date_from: date | None = (
            None if query.date_from is None else parse_local_date(query.date_from)
        )
        date_to: date | None = (
            None if query.date_to is None else parse_local_date(query.date_to)
        )
        if date_from is not None and date_to is not None and date_from > date_to:
            raise ValidationFailedError("The start date is after the end date.")

        return (
            None
            if date_from is None
            else local_day_start_microseconds(date_from, zone),
            None
            if date_to is None
            else local_day_start_microseconds(date_to + timedelta(days=1), zone),
        )

    def _messages_by_conversation(
        self,
        business: BusinessDocument,
    ) -> dict[ConversationId, list[MessageDocument]]:
        """Every message of the business by conversation, oldest first."""

        grouped: defaultdict[ConversationId, list[MessageDocument]] = defaultdict(
            list[MessageDocument]
        )
        for message in sorted(
            self._message_repo.list_by_business(business.id),
            key=lambda message: (int(message.created_at), str(message.id)),
        ):
            grouped[message.conversation_id].append(message)

        return dict(grouped)

    def _matches(
        self,
        search: str,
        conversation: ConversationDocument,
        contact: ContactDocument | None,
        messages: list[MessageDocument],
    ) -> bool:
        return matches_search(
            search,
            None if contact is None or contact.name is None else str(contact.name),
            None
            if contact is None or contact.phone_number is None
            else str(contact.phone_number),
            [str(message.text) for message in messages],
        )
