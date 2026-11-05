from base_pydantic_schemas import BaseDocument, PersistentDocument, SchemaVersion
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.value import TopicKind
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.insights.constrained_strings import TopicLabel
from app.schemas.typings.insights.prefixed_id import ConversationTopicsId
from app.schemas.typings.localization.constrained_strings import LanguageTag


class LocalizedTopicLabel(PersistentDocument):
    """A topic's label in one language (a cabinet language, or the owner's)."""

    language: LanguageTag
    label: TopicLabel


class ConversationTopic(PersistentDocument):
    """
    One thing customers ask about: its label in the owner's language (`label`,
    kept for the release before version 2), the same label in every cabinet
    language (`labels`), whether it is a named topic or the catch-all
    (`kind`), how many of the window's conversations opened with it, and how
    many of the questions the assistant could not answer (still open)
    belong to it.
    """

    label: TopicLabel
    kind: TopicKind = TopicKind.NAMED
    labels: list[LocalizedTopicLabel] = Field(default_factory=list[LocalizedTopicLabel])
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

    Version 2: every topic has a `kind` (the catch-all of other questions is
    OTHER, which the cabinet names in its own language) and `labels`, its
    label in each cabinet language (ka, ru, en) and the owner's, so a
    cabinet reads topics in its own language. Version 1 rows are upcast:
    their one label becomes the owner-language entry of `labels`, and a
    catch-all label ("Другие вопросы", "Other questions", ...) the OTHER kind.
    """

    schema_version: SchemaVersion = SchemaVersion("2")
    id: ConversationTopicsId
    business_id: BusinessId
    label_language: LanguageTag
    window_from: Microseconds
    window_to: Microseconds
    groups: list[TopicLanguageGroup] = Field(default_factory=list[TopicLanguageGroup])
