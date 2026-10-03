"""Shared steps of the team inbox use cases: audit entries and lookups."""

from typed_time_provider import Microseconds

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.inbox_repositories import (
    ConversationTeamRepoContract,
)
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.inbox import InboxRefusalCode
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.platform.constrained_strings import ErrorReasonCode
from app.schemas.typings.platform.strings import ErrorReasonMessage
from app.schemas.typings.users.prefixed_id import UserId

INBOX_ENTITY: AuditEntityName = AuditEntityName("inbox")
ASSIGNMENT_ENTITY: AuditEntityName = AuditEntityName("conversation_assignment")
NOTE_ENTITY: AuditEntityName = AuditEntityName("conversation_note")
QUICK_REPLY_ENTITY: AuditEntityName = AuditEntityName("quick_reply")
INBOX_SETTINGS_ENTITY: AuditEntityName = AuditEntityName("inbox_settings")
CONVERSATION_ENTITY: AuditEntityName = AuditEntityName("conversation")


def append_audit(
    audit_log_repo: AuditLogRepoContract,
    business_id: BusinessId,
    actor_id: UserId | None,
    action: AuditAction,
    entity: AuditEntityName,
    entity_reference: str | None,
    ip_address: ClientIpAddress | None,
    now: Microseconds,
) -> None:
    audit_log_repo.append(
        AuditLogEntryDocument(
            business_id=business_id,
            actor_id=actor_id,
            action=action,
            entity=entity,
            entity_id=(
                None
                if entity_reference is None
                else AuditEntityReference(entity_reference)
            ),
            ip_address=ip_address,
            created_at=now,
            updated_at=now,
        )
    )


def require_conversation(
    conversation_repo: ConversationTeamRepoContract,
    business_id: BusinessId,
    conversation_id: ConversationId,
) -> ConversationDocument:
    conversation: ConversationDocument | None = conversation_repo.get(
        business_id, conversation_id
    )
    if conversation is None:
        raise NotFoundError(f"Conversation {conversation_id} was not found.")

    return conversation


def member_of(business: BusinessDocument, user_id: UserId) -> BusinessMember | None:
    for member in business.members:
        if member.user_id == user_id:
            return member

    return None


def is_owner(business: BusinessDocument, user_id: UserId) -> bool:
    member: BusinessMember | None = member_of(business, user_id)
    return member is not None and member.role is BusinessMemberRole.OWNER


def require_members(
    business: BusinessDocument,
    user_ids: list[UserId],
) -> None:
    """ValidationFailedError (`not_a_member`) unless every user is a member."""

    strangers: list[UserId] = [
        user_id for user_id in user_ids if member_of(business, user_id) is None
    ]
    if strangers:
        raise ValidationFailedError(
            "Only members of the business can be assigned conversations.",
            reasons=[
                refusal(
                    InboxRefusalCode.NOT_A_MEMBER,
                    "Choose a member of the business's team.",
                )
            ],
        )


def refusal(code: InboxRefusalCode, message: str) -> ErrorReason:
    """One machine-readable reason of a refused inbox change."""

    return ErrorReason(
        code=ErrorReasonCode(code.value), message=ErrorReasonMessage(message)
    )
