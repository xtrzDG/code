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
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.conversation_feed.conversation_views import (
    ConversationListQuery,
    ConversationPage,
    ConversationSummaryView,
    ConversationViewSource,
)
from app.schemas.dto.listing_filters import ConversationFeedFilter
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.use_cases.conversations.feed.conversation_rows import build_view_sources
from app.use_cases.conversations.feed.feed_search_scan import SearchScan, scan_feed
from app.utilities.paging.keyset_paging import finish_page, read_slice
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
    the last message, not the messages themselves. Without a search a page
    is one keyset page read by the database; a search walks the feed in
    bounded batches (`feed_search_scan`).

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
        feed = ConversationFeedFilter(
            channel=input_data.channel,
            status=input_data.status,
            last_message_from=None
            if period_start is None
            else Microseconds(period_start),
            started_before=None if period_end is None else Microseconds(period_end),
            include_sandbox=input_data.include_sandbox,
        )
        page: list[ConversationDocument]
        next_cursor: PageCursor | None
        contacts: dict[ContactId, ContactDocument] | None = None
        if input_data.search is None:
            page, next_cursor = finish_page(
                self._conversation_repo.page_feed(
                    business.id, read_slice(input_data.page), feed
                ),
                input_data.page,
                sort_key=lambda conversation: int(conversation.last_message_at),
                item_id=lambda conversation: str(conversation.id),
            )
        else:
            scan: SearchScan = scan_feed(
                business.id,
                str(input_data.search),
                feed,
                input_data.page,
                self._conversation_repo,
                self._contact_repo,
                self._message_repo,
            )
            page, next_cursor, contacts = scan.matches, scan.next_cursor, scan.contacts

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
                self._summary_transformer.transform(source)
                for source in build_view_sources(
                    business.id,
                    page,
                    self._contact_repo,
                    self._message_repo,
                    contacts,
                )
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
