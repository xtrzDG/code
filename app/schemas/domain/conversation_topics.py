from base_pydantic_schemas import BaseDocument, PersistentDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.insights.constrained_strings import TopicLabel
from app.schemas.typings.insights.prefixed_id import ConversationTopicsId
from app.schemas.typings.localization.constrained_strings import LanguageTag


class ConversationTopic(PersistentDocument):
    """
    One thing customers ask about: its label in the owner's language, how
    many of the window's conversations opened with it, and how many of the
    questions the assistant could not answer (still open) belong to it.
    """

    label: TopicLabel
    conversation_count: PeriodItemCount
    unanswered_count: PeriodItemCount = PeriodItemCount(0)


class TopicLanguageGroup(PersistentDocument):
    """
    The topics of the conversations customers started in one language (None:
    the language was not known), most asked first, at most twelve, and how
    many conversations were grouped.
    """

    language: LanguageTag | None = None
    conversation_count: PeriodItemCount
    topics: list[ConversationTopic] = Field(default_factory=list[ConversationTopic])


class ConversationTopicsDocument(BaseDocument):
    """
    What customers of a business ask about: the first messages of the
    conversations started from `window_from` to `window_to` (the last 30
    days, sandbox left out), grouped by a cheap model into labelled topics
    per customer language, labels written in `label_language` (the owner's).
    One document per business (the id derives from it); every night's
    grouping replaces it. Labels and counts only: no customer text is kept.
    """

    id: ConversationTopicsId
    business_id: BusinessId
    label_language: LanguageTag
    window_from: Microseconds
    window_to: Microseconds
    groups: list[TopicLanguageGroup] = Field(default_factory=list[TopicLanguageGroup])
