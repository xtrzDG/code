from base_pydantic_schemas import BaseDocument, PersistentDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.inbox.constrained_strings import (
    QuickReplyShortcut,
    QuickReplyTemplateText,
    QuickReplyTitle,
)
from app.schemas.typings.inbox.prefixed_id import QuickReplyId, QuickReplyLibraryId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId


class QuickReplyVariant(PersistentDocument):
    """A saved reply in one language."""

    language: LanguageTag
    text: QuickReplyTemplateText


class QuickReply(PersistentDocument):
    """
    One saved reply: the shortcut staff type after "/", its name in the
    picker and its text in one or more languages (one variant per language;
    the conversation's language picks the variant).
    """

    id: QuickReplyId = Field(default_factory=QuickReplyId)
    shortcut: QuickReplyShortcut
    title: QuickReplyTitle
    variants: list[QuickReplyVariant]
    created_by: UserId
    created_at: Microseconds
    updated_at: Microseconds


class QuickReplyLibraryDocument(BaseDocument):
    """
    The saved replies of one business, kept together in the owner's order
    (one document per business, the id derived from it): a change reads and
    writes the whole library in one step, so shortcuts stay unique and the
    limit holds even when two owners edit at once. Owners edit it; staff
    read it.
    """

    id: QuickReplyLibraryId
    business_id: BusinessId
    replies: list[QuickReply] = Field(default_factory=list[QuickReply])
