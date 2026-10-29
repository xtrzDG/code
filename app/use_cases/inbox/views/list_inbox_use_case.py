from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.inbox_repositories import (
    ConversationNoteRepoContract,
    ConversationTeamRepoContract,
    InboxWorkRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.inbox.inbox_views import (
    InboxItemSource,
    InboxItemView,
    InboxPage,
    InboxQuery,
    InboxViewFilter,
)
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.use_cases.inbox.inbox_support import INBOX_ENTITY, append_audit
from app.use_cases.inbox.views.inbox_rows import build_inbox_sources
from app.utilities.paging.keyset_paging import finish_page, read_slice


class ListInboxUseCase(UseCaseContract[InboxQuery, InboxPage]):
    """
    One page of a view of the team inbox (`InboxView`: needs a person,
    requests, mine, unassigned, all), the latest message first, keyset
    paged in the database on `last_message_at`, with the counts of the
    views. Owners and staff see the same conversations; "mine" is the
    viewer's.

    Rows are the staff-safe projection (`InboxItemTransformer`). They show
    customers' names, phones and message beginnings, so every page is
    audited as the viewer's view of the inbox (entity "inbox", the view's
    name as the reference): who looked at which queue, and when.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        conversation_repo: ConversationTeamRepoContract,
        contact_repo: ContactRepoContract,
        message_repo: MessageRepoContract,
        note_repo: ConversationNoteRepoContract,
        inbox_work_repo: InboxWorkRepoContract,
        item_transformer: TransformerContract[InboxItemSource, InboxItemView],
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._conversation_repo: ConversationTeamRepoContract = conversation_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._message_repo: MessageRepoContract = message_repo
        self._note_repo: ConversationNoteRepoContract = note_repo
        self._inbox_work_repo: InboxWorkRepoContract = inbox_work_repo
        self._item_transformer: TransformerContract[InboxItemSource, InboxItemView] = (
            item_transformer
        )
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: InboxQuery) -> InboxPage:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        page: list[ConversationDocument]
        next_cursor: PageCursor | None
        page, next_cursor = finish_page(
            self._conversation_repo.page_inbox(
                business.id,
                read_slice(input_data.page),
                InboxViewFilter(
                    view=input_data.view,
                    viewer=input_data.user_id,
                    channel=input_data.channel,
                ),
            ),
            input_data.page,
            sort_key=lambda conversation: int(conversation.last_message_at),
            item_id=lambda conversation: str(conversation.id),
        )
        append_audit(
            self._audit_log_repo,
            business.id,
            input_data.user_id,
            AuditAction.VIEW,
            INBOX_ENTITY,
            input_data.view.value,
            input_data.client_ip_address,
            self._wall_clock.now_unix(),
        )
        return InboxPage(
            view=input_data.view,
            items=[
                self._item_transformer.transform(source)
                for source in build_inbox_sources(
                    business.id,
                    page,
                    self._contact_repo,
                    self._message_repo,
                    self._note_repo,
                    self._inbox_work_repo,
                )
            ],
            counts=self._conversation_repo.count_inbox(business.id, input_data.user_id),
            next_cursor=next_cursor,
        )
