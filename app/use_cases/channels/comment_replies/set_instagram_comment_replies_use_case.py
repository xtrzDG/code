from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument, InstagramCommentReplies
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.channels.channel_settings import ChannelView
from app.schemas.dto.channels.comment_replies import (
    InstagramCommentRepliesRequest,
    SetInstagramCommentRepliesCommand,
)
from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.platform.constrained_strings import ErrorReasonCode
from app.schemas.typings.platform.strings import ErrorReasonMessage
from app.use_cases.channels.channel_views import build_channel_view
from app.utilities.channels.channel_health import is_channel_active
from app.utilities.channels.comment_keywords import distinct_keywords
from app.utilities.channels.delivery_targets import find_business_channel

KEYWORDS_MISSING: str = "comment_keywords_missing"
REPLY_MISSING: str = "comment_reply_missing"


class SetInstagramCommentRepliesUseCase(
    UseCaseContract[SetInstagramCommentRepliesCommand, ChannelView]
):
    """
    The owner sets the Instagram card's comment-to-DM: on or off, the
    keywords (each once, letter case aside) and the private reply. Turning
    it on needs a keyword and a reply (`comment_keywords_missing`,
    `comment_reply_missing`); off keeps both for later. Only a connected
    Instagram account has it. The change is written to the audit log.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        channel_repo: ChannelRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._channel_repo: ChannelRepoContract = channel_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: SetInstagramCommentRepliesCommand) -> ChannelView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        replies: InstagramCommentReplies = checked_replies(input_data.request)
        channel: ChannelDocument | None = find_business_channel(
            self._channel_repo, business.id, ChannelKind.INSTAGRAM
        )
        if channel is None or not is_channel_active(channel):
            raise NotFoundError("Connect Instagram before setting comment replies.")

        now: Microseconds = self._wall_clock.now_unix()

        def set_replies(stored: ChannelDocument) -> ChannelDocument | None:
            return stored.model_copy(
                update={"comment_replies": replies, "updated_at": now}
            )

        saved: ChannelDocument | None = self._channel_repo.modify(
            business.id, channel.id, set_replies
        )
        if saved is None:
            raise NotFoundError("Connect Instagram before setting comment replies.")

        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.UPDATE,
                entity=AuditEntityName("channel"),
                entity_id=AuditEntityReference(str(channel.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return build_channel_view(saved)


def checked_replies(request: InstagramCommentRepliesRequest) -> InstagramCommentReplies:
    """The settings to store; turning on without keywords or reply is refused."""

    keywords = distinct_keywords(list(request.keywords))
    reasons: list[ErrorReason] = []
    if request.is_on and not keywords:
        reasons.append(
            refusal(KEYWORDS_MISSING, "Add at least one keyword to listen for.")
        )
    if request.is_on and request.reply_text is None:
        reasons.append(refusal(REPLY_MISSING, "Write the private reply to send."))
    if reasons:
        raise ValidationFailedError(
            "Comment replies need keywords and a reply to be turned on.",
            reasons=reasons,
        )

    return InstagramCommentReplies(
        is_on=request.is_on, keywords=keywords, reply_text=request.reply_text
    )


def refusal(code: str, message: str) -> ErrorReason:
    return ErrorReason(code=ErrorReasonCode(code), message=ErrorReasonMessage(message))
