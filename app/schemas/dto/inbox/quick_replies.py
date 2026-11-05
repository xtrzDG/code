"""Saved replies of a business: owners edit them, the team uses them."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.inbox import QuickReplyVariable
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.inbox.constrained_strings import (
    QuickReplyShortcut,
    QuickReplyTemplateText,
    QuickReplyTitle,
)
from app.schemas.typings.inbox.prefixed_id import QuickReplyId
from app.schemas.typings.inbox.strings import QuickReplyFilledText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId

# Variants of one saved reply: one per language.
MAX_QUICK_REPLY_VARIANTS: int = 12


class QuickReplyVariantInput(ImmutableDTO):
    """The text of a saved reply in one language."""

    language: LanguageTag
    text: QuickReplyTemplateText


class QuickReplyRequest(ImmutableDTO):
    """
    Body of POST and PUT .../quick-replies: the shortcut typed after "/",
    the name in the picker and the text in each language (one variant per
    language). Texts may carry {name}, {booking_time} and {business_name}.
    """

    shortcut: QuickReplyShortcut
    title: QuickReplyTitle
    variants: list[QuickReplyVariantInput] = Field(
        min_length=1, max_length=MAX_QUICK_REPLY_VARIANTS
    )


class SaveQuickReplyCommand(ImmutableDTO):
    """
    An owner creates a saved reply (`quick_reply_id` None) or replaces one.
    """

    user_id: UserId
    business_id: BusinessId
    quick_reply_id: QuickReplyId | None = None
    request: QuickReplyRequest
    client_ip_address: ClientIpAddress | None = None


class DeleteQuickReplyCommand(ImmutableDTO):
    """An owner deletes a saved reply."""

    user_id: UserId
    business_id: BusinessId
    quick_reply_id: QuickReplyId
    client_ip_address: ClientIpAddress | None = None


class QuickRepliesQuery(ImmutableDTO):
    """The saved replies of a business (owners and staff)."""

    user_id: UserId
    business_id: BusinessId


class QuickReplyVariantView(ImmutableDTO):
    """A saved reply in one language."""

    language: LanguageTag
    text: QuickReplyTemplateText


class QuickReplyView(ImmutableDTO):
    """A saved reply with the variables its texts use."""

    id: QuickReplyId
    shortcut: QuickReplyShortcut
    title: QuickReplyTitle
    variants: list[QuickReplyVariantView]
    variables: list[QuickReplyVariable] = Field(
        default_factory=list[QuickReplyVariable]
    )
    created_by: UserId
    updated_at: Microseconds


class QuickReplyList(ImmutableDTO):
    """The saved replies of a business in the owner's order."""

    items: list[QuickReplyView] = Field(default_factory=list[QuickReplyView])


class ConversationQuickRepliesQuery(ImmutableDTO):
    """
    The saved replies ready to send in one conversation: in its language,
    with the customer's name and booking filled in (audited as a view of
    the conversation's customer).
    """

    user_id: UserId
    business_id: BusinessId
    conversation_id: ConversationId
    client_ip_address: ClientIpAddress | None = None


class FilledQuickReplyView(ImmutableDTO):
    """
    A saved reply for one conversation: the variant of the conversation's
    language (else its base language, the business's default language, then
    the first variant) with its variables filled in. `missing_variables`
    stayed in braces because the conversation has no value for them (no
    name yet, no upcoming booking): staff complete them before sending.
    """

    id: QuickReplyId
    shortcut: QuickReplyShortcut
    title: QuickReplyTitle
    language: LanguageTag
    text: QuickReplyFilledText
    missing_variables: list[QuickReplyVariable] = Field(
        default_factory=list[QuickReplyVariable]
    )


class FilledQuickReplyList(ImmutableDTO):
    """The saved replies of a business ready for one conversation."""

    conversation_id: ConversationId
    items: list[FilledQuickReplyView] = Field(
        default_factory=list[FilledQuickReplyView]
    )
