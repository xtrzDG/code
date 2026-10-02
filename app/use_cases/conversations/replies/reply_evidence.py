"""What the model is told and what backs its reply, read from the messages."""

from app.contracts.repositories.conversation_repositories import MessageRepoContract
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import LlmTurnDocument
from app.schemas.dto.conversation_engine import PreparedTurn
from app.schemas.typings.conversations.strings import (
    MessageText,
    UnverifiedReplyValue,
)
from app.use_cases.conversations.replies.turn_progress import TurnProgress
from app.utilities.conversations.turn_context import EarlierMessage
from app.utilities.reply_guard.invented_numbers import find_unverified_values


def collect_unanswered_messages(
    message_repo: MessageRepoContract,
    turn: PreparedTurn,
    stored_turns: list[LlmTurnDocument],
) -> list[EarlierMessage]:
    """
    Messages after the last model turn and before this one: the customer
    messages the assistant stayed silent on (handoff, hourly limit) and
    what staff wrote meanwhile, which the model never saw otherwise.
    """

    last_turn_at: int = int(stored_turns[-1].created_at) if stored_turns else -1
    return [
        EarlierMessage(
            text=str(message.text),
            is_from_staff=message.author is MessageAuthor.STAFF,
        )
        for message in sorted(
            message_repo.list_by_conversation(turn.business.id, turn.conversation.id),
            key=lambda message: int(message.created_at),
        )
        if (
            message.direction is MessageDirection.INBOUND
            or message.author is MessageAuthor.STAFF
        )
        and last_turn_at < int(message.created_at) < int(turn.received_at)
    ]


def find_unverified_reply_values(
    message_repo: MessageRepoContract,
    turn: PreparedTurn,
    progress: TurnProgress,
    text: MessageText,
) -> list[UnverifiedReplyValue]:
    """Values of the reply text that no evidence of the conversation backs."""

    # Trusted: what the business and the server said.
    evidence: list[str] = [
        str(turn.business.name),
        str(turn.context_line),
        *(f"{fact.label}: {fact.value}" for fact in turn.version.facts),
        *progress.tool_results,
    ]
    # What the customer wrote, and earlier replies (which may repeat it):
    # they back times, dates, phones and counts, never a price.
    customer_texts: list[str] = []
    for message in message_repo.list_by_conversation(
        turn.business.id, turn.conversation.id
    ):
        if message.direction is MessageDirection.INBOUND:
            customer_texts.append(str(message.text))
            continue

        if message.author is MessageAuthor.ASSISTANT:
            customer_texts.append(str(message.text))

        # Staff are the business speaking: the assistant may repeat their
        # prices and terms.
        if message.author is MessageAuthor.STAFF:
            evidence.append(str(message.text))

        # Tool results of earlier replies and of voice-agent calls count.
        evidence.extend(
            str(record.result_json)
            for record in message.tool_calls
            if not record.is_error
        )

    return find_unverified_values(
        text,
        evidence,
        [*turn.version.languages, turn.language],
        [turn.business.currency_code],
        customer_texts=customer_texts,
    )
