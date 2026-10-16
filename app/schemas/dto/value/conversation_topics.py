"""What customers of a business ask about (the Overview card), as last grouped."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.value import TopicKind
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.insights.constrained_strings import TopicLabel
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId


class ConversationTopicsQuery(ImmutableDTO):
    """The topics for a member reading the cabinet in `language` (None: the owner's)."""

    user_id: UserId
    business_id: BusinessId
    language: LanguageTag | None = None


class ConversationTopicView(ImmutableDTO):
    """
    One topic: its label in the reader's language, whether it is a named
    topic or the catch-all of other questions (OTHER, which the cabinet
    names from its own dictionary; `label` is its text in the reader's
    language), the conversations that opened with it and the open questions
    the assistant could not answer.
    """

    label: TopicLabel
    kind: TopicKind = TopicKind.NAMED
    conversation_count: PeriodItemCount
    unanswered_count: PeriodItemCount


class TopicLanguageView(ImmutableDTO):
    """The topics of the conversations started in one customer language."""

    language: LanguageTag | None = None
    conversation_count: PeriodItemCount
    topics: list[ConversationTopicView] = Field(
        default_factory=list[ConversationTopicView]
    )


class ConversationTopicsView(ImmutableDTO):
    """
    The topics of the conversations started from `window_from` to
    `window_to` (the last 30 days when grouped, every night), largest
    language first, labelled in `label_language` (the reader's). Never
    grouped yet: no window and no groups.
    """

    business_id: BusinessId
    label_language: LanguageTag
    window_from: Microseconds | None = None
    window_to: Microseconds | None = None
    groups: list[TopicLanguageView] = Field(default_factory=list[TopicLanguageView])
