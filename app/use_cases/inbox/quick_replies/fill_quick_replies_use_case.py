from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.repositories.inbox_repositories import (
    ConversationTeamRepoContract,
    QuickReplyLibraryRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.inbox import QuickReplyVariable
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.quick_replies import (
    QuickReplyLibraryDocument,
    QuickReplyVariant,
)
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.inbox.quick_replies import (
    ConversationQuickRepliesQuery,
    FilledQuickReplyList,
    FilledQuickReplyView,
)
from app.schemas.typings.inbox.strings import QuickReplyFilledText
from app.use_cases.inbox.inbox_support import (
    CONVERSATION_ENTITY,
    append_audit,
    require_conversation,
)
from app.use_cases.inbox.quick_replies.reply_values import (
    next_booking_start,
    variable_values,
)
from app.utilities.inbox.quick_reply_templates import choose_variant, fill_variables


class FillQuickRepliesUseCase(
    UseCaseContract[ConversationQuickRepliesQuery, FilledQuickReplyList]
):
    """
    The saved replies ready to send in one conversation (the "/" picker of
    the composer): for each, the variant of the conversation's language
    (`choose_variant`) with {name} (the customer's name), {booking_time}
    (the start of the conversation's next booking, in the business time
    zone and the variant's language) and {business_name} filled in. A
    variable without a value stays in braces and is listed, so staff
    complete it instead of sending a guess. Reading the customer's name and
    booking for this is audited as a view of the conversation.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        conversation_repo: ConversationTeamRepoContract,
        contact_repo: ContactRepoContract,
        booking_repo: BookingRepoContract,
        quick_reply_library_repo: QuickReplyLibraryRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._conversation_repo: ConversationTeamRepoContract = conversation_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._quick_reply_library_repo: QuickReplyLibraryRepoContract = (
            quick_reply_library_repo
        )
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ConversationQuickRepliesQuery) -> FilledQuickReplyList:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        conversation: ConversationDocument = require_conversation(
            self._conversation_repo, business.id, input_data.conversation_id
        )
        library: QuickReplyLibraryDocument | None = (
            self._quick_reply_library_repo.get_by_business(business.id)
        )
        if library is None or not library.replies:
            return FilledQuickReplyList(conversation_id=conversation.id)

        now: Microseconds = self._wall_clock.now_unix()
        contact: ContactDocument | None = self._contact_repo.get(
            business.id, conversation.contact_id
        )
        booking_start = next_booking_start(
            self._booking_repo.list_by_conversation(business.id, conversation.id), now
        )
        append_audit(
            self._audit_log_repo,
            business.id,
            input_data.user_id,
            AuditAction.VIEW,
            CONVERSATION_ENTITY,
            str(conversation.id),
            input_data.client_ip_address,
            now,
        )
        items: list[FilledQuickReplyView] = []
        for reply in library.replies:
            variant: QuickReplyVariant = choose_variant(
                reply.variants, conversation.language, business.default_language
            )
            values: dict[QuickReplyVariable, str] = variable_values(
                business, contact, booking_start, variant.language
            )
            text, missing = fill_variables(str(variant.text), values)
            items.append(
                FilledQuickReplyView(
                    id=reply.id,
                    shortcut=reply.shortcut,
                    title=reply.title,
                    language=variant.language,
                    text=QuickReplyFilledText(text),
                    missing_variables=missing,
                )
            )

        return FilledQuickReplyList(conversation_id=conversation.id, items=items)
