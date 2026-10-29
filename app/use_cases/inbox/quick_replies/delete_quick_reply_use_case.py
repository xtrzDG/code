from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.inbox_repositories import (
    QuickReplyLibraryRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.quick_replies import QuickReplyLibraryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.inbox.quick_replies import DeleteQuickReplyCommand, QuickReplyList
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.inbox.inbox_support import QUICK_REPLY_ENTITY, append_audit
from app.use_cases.inbox.quick_replies.quick_reply_views import (
    build_quick_reply_list,
)


class DeleteQuickReplyUseCase(UseCaseContract[DeleteQuickReplyCommand, QuickReplyList]):
    """An owner deletes a saved reply (audited); the remaining ones are returned."""

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

    def run(self, input_data: DeleteQuickReplyCommand) -> QuickReplyList:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        current = self._quick_reply_library_repo.get_by_business(business.id)
        if current is None or all(
            reply.id != input_data.quick_reply_id for reply in current.replies
        ):
            raise NotFoundError(
                f"Saved reply {input_data.quick_reply_id} was not found."
            )

        now: Microseconds = self._wall_clock.now_unix()

        def remove(library: QuickReplyLibraryDocument) -> None:
            library.replies = [
                reply
                for reply in library.replies
                if reply.id != input_data.quick_reply_id
            ]

        library = self._quick_reply_library_repo.change(business.id, remove, now)
        append_audit(
            self._audit_log_repo,
            business.id,
            input_data.user_id,
            AuditAction.DELETE,
            QUICK_REPLY_ENTITY,
            str(input_data.quick_reply_id),
            input_data.client_ip_address,
            now,
        )
        return build_quick_reply_list(library)
