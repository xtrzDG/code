"""What the model is told and what backs its reply, read from the messages."""

from dataclasses import dataclass

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
from app.utilities.media.attachment_texts import (
    describe_message_for_model,
    readable_message_text,
)
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
            text=describe_message_for_model(str(message.text), message.attachments),
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


@dataclass(frozen=True)
class ReplyEvidence:
    """
    What backs a reply, read from the conversation once (technical record).

    `trusted`: what the business and the server said (the business name,
    the context line, the facts, tool results and staff messages).
    `customer`: what the customer wrote and the assistant repeated; it
    backs times, dates, phones and counts, never a price. `own_contact`:
    where the customer's own and the business's public contact details
    may come from (no staff messages: staff may quote other customers).
    """

    trusted: list[str]
    customer: list[str]
    own_contact: list[str]


def gather_reply_evidence(
    message_repo: MessageRepoContract,
    turn: PreparedTurn,
    progress: TurnProgress,
) -> ReplyEvidence:
    """The evidence of the conversation's stored messages and this turn."""

    business_texts: list[str] = [
        str(turn.business.name),
        str(turn.context_line),
        *(f"{fact.label}: {fact.value}" for fact in turn.version.facts),
        *progress.tool_results,
    ]
    staff_texts: list[str] = []
    tool_texts: list[str] = []
    customer_written: list[str] = [str(turn.customer_text)]
    assistant_texts: list[str] = []
    for message in message_repo.list_by_conversation(
        turn.business.id, turn.conversation.id
    ):
        if message.direction is MessageDirection.INBOUND:
            # Voice-note transcripts and shared places are the customer's
            # words too.
            customer_written.append(
                readable_message_text(str(message.text), message.attachments)
            )
            continue

        if message.author is MessageAuthor.ASSISTANT:
            assistant_texts.append(str(message.text))

        # Staff are the business speaking: the assistant may repeat their
        # prices and terms.
        if message.author is MessageAuthor.STAFF:
            staff_texts.append(str(message.text))

        # Tool results of earlier replies and of voice-agent calls count.
        tool_texts.extend(
            str(record.result_json)
            for record in message.tool_calls
            if not record.is_error
        )

    return ReplyEvidence(
        trusted=[*business_texts, *staff_texts, *tool_texts],
        customer=[*customer_written, *assistant_texts],
        own_contact=[*business_texts, *tool_texts, *customer_written],
    )


def find_unverified_reply_values(
    evidence: ReplyEvidence,
    turn: PreparedTurn,
    text: MessageText,
) -> list[UnverifiedReplyValue]:
    """Values of the reply text that no evidence of the conversation backs."""

    return find_unverified_values(
        text,
        evidence.trusted,
        [*turn.version.languages, turn.reply_language],
        [turn.business.currency_code],
        customer_texts=evidence.customer,
    )
