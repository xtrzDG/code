"""
"Fix this answer" on an assistant reply: what the cabinet's dialog starts
from, what the owner sends, and the knowledge item it became.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.knowledge import AnswerCorrectionScope, KnowledgeItemKind
from app.schemas.constants.reply_safety import ReplyGuardReason
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.conversations.booleans import IsAnswerCorrected
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.knowledge.booleans import IsNewKnowledgeItem
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.users.prefixed_id import UserId


class AnswerCorrectionQuery(ImmutableDTO):
    """The owner opens "Fix this answer" on an assistant reply (audited)."""

    user_id: UserId
    business_id: BusinessId
    conversation_id: ConversationId
    message_id: MessageId
    client_ip_address: ClientIpAddress | None = None


class CorrectionFactView(ImmutableDTO):
    """A knowledge item as the correction dialog shows it."""

    knowledge_item_id: KnowledgeItemId
    kind: KnowledgeItemKind
    title: KnowledgeTitle
    body: KnowledgeBody | None = None
    price_minor: MoneyAmountMinor | None = None
    currency_code: CurrencyCode | None = None


class AnswerCorrectionDraft(ImmutableDTO):
    """
    What the dialog opens with: the customer's question before the answer
    (None when the answer opened the conversation), the answer, the kind
    of correction it suggests, and the current fact the answer came from
    (the item an earlier correction of this answer made, else the item the
    assistant looked up or whose title the question names). `guard_reasons`
    say why the reply guard held the answer back, if it did.
    """

    conversation_id: ConversationId
    message_id: MessageId
    question: KnowledgeTitle | None = None
    answer: MessageText
    language: LanguageTag | None = None
    suggested_scope: AnswerCorrectionScope
    current_fact: CorrectionFactView | None = None
    is_corrected: IsAnswerCorrected = False
    guard_reasons: list[ReplyGuardReason] = Field(
        default_factory=list[ReplyGuardReason]
    )


class AnswerCorrectionRequest(ImmutableDTO):
    """
    HTTP body of "Fix this answer". FAQ, HOURS and RULE take the customer's
    `question` (the item title) and the `correct_answer`; PRICE takes the
    new `price_minor` of the offer `knowledge_item_id`, or of a new offer
    named `question` (with `correct_answer` as its description).
    """

    scope: AnswerCorrectionScope
    question: KnowledgeTitle | None = None
    correct_answer: KnowledgeBody | None = None
    knowledge_item_id: KnowledgeItemId | None = None
    price_minor: MoneyAmountMinor | None = None


class CorrectAnswerCommand(ImmutableDTO):
    """The owner corrects an assistant answer."""

    user_id: UserId
    business_id: BusinessId
    conversation_id: ConversationId
    message_id: MessageId
    request: AnswerCorrectionRequest


class AnswerCorrectionResult(ImmutableDTO):
    """
    The knowledge item the correction created (`is_new`) or updated; it
    reaches customers with the next "Apply changes". `question` and
    `language` are what a check saved from the correction asks.
    """

    conversation_id: ConversationId
    message_id: MessageId
    item: CorrectionFactView
    is_new: IsNewKnowledgeItem
    question: KnowledgeTitle
    language: LanguageTag
