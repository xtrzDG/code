from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.inbox_repositories import (
    QuickReplyLibraryRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.quick_replies import (
    QuickReply,
    QuickReplyLibraryDocument,
    QuickReplyVariant,
)
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.inbox.quick_replies import QuickReplyView, SaveQuickReplyCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.inbox.prefixed_id import QuickReplyId
from app.use_cases.inbox.inbox_support import (
    QUICK_REPLY_ENTITY,
    append_audit,
)
from app.use_cases.inbox.quick_replies.quick_reply_views import (
    build_quick_reply_view,
    check_place_in,
    check_texts,
)


class SaveQuickReplyUseCase(UseCaseContract[SaveQuickReplyCommand, QuickReplyView]):
    """
    An owner adds a saved reply (at the end of the list) or replaces one:
    a shortcut unique within the business (ignoring case, 409
    `shortcut_taken`), a title, and one text per language (422
    `duplicate_language`) whose variables are ones the inbox fills (422
    `unknown_variable`); at most 100 replies (409
    `too_many_quick_replies`). The whole library changes in one step, so
    two owners editing at once cannot break these rules. Audited (CREATE or
    UPDATE of "quick_reply").
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        quick_reply_library_repo: QuickReplyLibraryRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._quick_reply_library_repo: QuickReplyLibraryRepoContract = (
            quick_reply_library_repo
        )
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: SaveQuickReplyCommand) -> QuickReplyView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        check_texts(input_data.request)
        now: Microseconds = self._wall_clock.now_unix()
        replacing: QuickReplyId | None = input_data.quick_reply_id
        if replacing is not None:
            current = self._quick_reply_library_repo.get_by_business(business.id)
            if current is None or find_reply(current, replacing) is None:
                raise NotFoundError(f"Saved reply {replacing} was not found.")

        saved_id: QuickReplyId = replacing or QuickReplyId()

        def save(library: QuickReplyLibraryDocument) -> None:
            check_place_in(library, input_data.request, replacing)
            previous: QuickReply | None = find_reply(library, saved_id)
            if replacing is not None and previous is None:
                raise NotFoundError(f"Saved reply {replacing} was not found.")

            reply = QuickReply(
                id=saved_id,
                shortcut=input_data.request.shortcut,
                title=input_data.request.title,
                variants=[
                    QuickReplyVariant(language=variant.language, text=variant.text)
                    for variant in input_data.request.variants
                ],
                created_by=input_data.user_id
                if previous is None
                else previous.created_by,
                created_at=now if previous is None else previous.created_at,
                updated_at=now,
            )
            if previous is None:
                library.replies = [*library.replies, reply]
            else:
                library.replies = [
                    reply if stored.id == saved_id else stored
                    for stored in library.replies
                ]

        library = self._quick_reply_library_repo.change(business.id, save, now)
        append_audit(
            self._audit_log_repo,
            business.id,
            input_data.user_id,
            AuditAction.CREATE if replacing is None else AuditAction.UPDATE,
            QUICK_REPLY_ENTITY,
            str(saved_id),
            input_data.client_ip_address,
            now,
        )
        stored: QuickReply | None = find_reply(library, saved_id)
        if stored is None:
            raise NotFoundError(f"Saved reply {saved_id} was not found.")

        return build_quick_reply_view(stored)


def find_reply(
    library: QuickReplyLibraryDocument, reply_id: QuickReplyId
) -> QuickReply | None:
    for reply in library.replies:
        if reply.id == reply_id:
            return reply

    return None
