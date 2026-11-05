"""
One stored message of a demo conversation: who wrote it, what the model
reply cost, how long the customer waited for it, and what the reply guard
did with it (as the live engine stores each of those).
"""

from typed_time_provider import Microseconds

from app.registries.demo.demo_reply_speed import demo_reply_channel, demo_reply_latency
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import MessageAuthor, ReplyGuardVerdict
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.message_media import MessageAttachment
from app.schemas.dto.demo_data import DemoMessageLine, DemoReplyGuard
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.users.prefixed_id import UserId

# What an assistant reply of gpt-5-mini roughly costs: the cached
# instruction and transcript in, a short answer out.
REPLY_INPUT_TOKENS: int = 2600
INPUT_MICRO_USD_PER_TOKEN: float = 0.25
OUTPUT_MICRO_USD_PER_TOKEN: float = 2.0
CHARACTERS_PER_TOKEN: int = 3
# A reply the guard let through as written.
CLEAN_REPLY: DemoReplyGuard = DemoReplyGuard(verdict=ReplyGuardVerdict.CLEAN)


def demo_message(
    conversation: ConversationDocument,
    line: DemoMessageLine,
    position: int,
    moment: Microseconds,
    message_id: MessageId,
    attachments: list[MessageAttachment],
    model_id: LlmModelId,
    team_member_id: UserId,
) -> MessageDocument:
    """
    The message of line `position` of a conversation at `moment`: a model
    reply with its usage, cost, wait and the guard's verdict from the line
    (clean when the line names none).
    """

    is_model_reply: bool = line.author is MessageAuthor.ASSISTANT
    output_tokens: int = len(str(line.text)) // CHARACTERS_PER_TOKEN + 20
    guard: DemoReplyGuard | None = (
        (line.guard or CLEAN_REPLY) if is_model_reply else None
    )
    return MessageDocument(
        id=message_id,
        conversation_id=conversation.id,
        business_id=conversation.business_id,
        direction=(
            MessageDirection.INBOUND
            if line.author is MessageAuthor.CUSTOMER
            else MessageDirection.OUTBOUND
        ),
        author=line.author,
        text=line.text,
        language=conversation.language,
        sent_by=team_member_id if line.author is MessageAuthor.STAFF else None,
        tool_calls=list(line.tool_calls),
        attachments=attachments,
        model_id=model_id if is_model_reply else None,
        channel=demo_reply_channel(conversation, line),
        reply_latency_ms=demo_reply_latency(conversation, line, position),
        guard_verdict=None if guard is None else guard.verdict,
        guard_reasons=[] if guard is None else list(guard.reasons),
        unverified_values=[] if guard is None else list(guard.unverified_values),
        claim_findings=[] if guard is None else list(guard.claim_findings),
        input_tokens=LlmTokenCount(REPLY_INPUT_TOKENS if is_model_reply else 0),
        output_tokens=LlmTokenCount(output_tokens if is_model_reply else 0),
        cost_micro_usd=CostMicroUsd(
            round(
                REPLY_INPUT_TOKENS * INPUT_MICRO_USD_PER_TOKEN
                + output_tokens * OUTPUT_MICRO_USD_PER_TOKEN
            )
            if is_model_reply
            else 0
        ),
        created_at=moment,
        updated_at=moment,
    )
