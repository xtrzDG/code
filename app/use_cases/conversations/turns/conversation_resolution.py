"""The conversation a customer message belongs to: an open one, or a new one."""

from datetime import timedelta

from typed_time_provider import Microseconds

from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.conversations import InboundMessage
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.use_cases.conversations.turns.turn_time import to_microseconds

CONVERSATION_WINDOW: timedelta = timedelta(hours=24)


def resolve_conversation(
    conversation_repo: ConversationRepoContract,
    assistant_version_repo: AssistantVersionRepoContract,
    business: BusinessDocument,
    contact: ContactDocument,
    message: InboundMessage,
    is_sandbox: bool,
    now: Microseconds,
) -> tuple[ConversationDocument, bool]:
    """
    The open conversation (see `find_open_conversation`) unless the message
    asks for another version; else a new one pinned to the requested or
    published version. Returns it and whether it is new.

    Raises:
        ConflictError: the business has no published version.
        NotFoundError: the version does not exist.
    """

    open_conversation: ConversationDocument | None = find_open_conversation(
        conversation_repo, business, contact, message.channel, is_sandbox, now
    )
    requested_version_id: AssistantVersionId | None = message.assistant_version_id
    if open_conversation is not None and (
        requested_version_id is None
        or requested_version_id == open_conversation.assistant_version_id
    ):
        return open_conversation, False

    version_id: AssistantVersionId | None = (
        requested_version_id
        if requested_version_id is not None
        else business.published_assistant_version_id
    )
    if version_id is None:
        raise ConflictError(f"{business.name} has no published assistant version yet.")

    if assistant_version_repo.get(business.id, version_id) is None:
        raise NotFoundError(f"Assistant version {version_id} was not found.")

    conversation = ConversationDocument(
        business_id=business.id,
        contact_id=contact.id,
        assistant_version_id=version_id,
        channel=message.channel,
        channel_user_id=message.channel_user_id,
        is_sandbox=is_sandbox,
        last_message_at=now,
        created_at=now,
        updated_at=now,
    )
    conversation_repo.save(conversation)
    return conversation, True


def find_open_conversation(
    conversation_repo: ConversationRepoContract,
    business: BusinessDocument,
    contact: ContactDocument,
    channel: ChannelKind,
    is_sandbox: bool,
    now: Microseconds,
) -> ConversationDocument | None:
    """
    The contact's conversation in this channel and sandbox mode that staff
    still own (HANDOFF, however long ago), else one with a message in the
    last 24 hours.
    """

    window_start: int = int(now) - to_microseconds(CONVERSATION_WINDOW)
    recent: ConversationDocument | None = None
    for conversation in conversation_repo.list_by_business(business.id):
        if (
            conversation.contact_id != contact.id
            or conversation.channel is not channel
            or conversation.is_sandbox != is_sandbox
            or conversation.status is ConversationStatus.CLOSED
        ):
            continue

        # Staff own it until they close the handoff, however long ago.
        if conversation.status is ConversationStatus.HANDOFF:
            return conversation

        if recent is None and int(conversation.last_message_at) >= window_start:
            recent = conversation

    return recent
