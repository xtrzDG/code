"""
Aliases of knowledge items suggested by a language model: the titles of a
business's items in its other languages, for the owner to review.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.knowledge.booleans import IsAliasAnswerReadable
from app.schemas.typings.knowledge.constrained_strings import KnowledgeAliasText
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId


class AliasSuggestionItem(ImmutableDTO):
    """
    One item to name in other languages: its title, the languages it is
    written in and the languages it needs an alias in.
    """

    item_id: KnowledgeItemId
    kind: KnowledgeItemKind
    title: KnowledgeTitle
    source_languages: list[LanguageTag]
    target_languages: list[LanguageTag]


class AliasSuggestionRequest(ImmutableDTO):
    """The items of one model call (at most `MAX_ITEMS_PER_CALL`)."""

    items: list[AliasSuggestionItem]


class SuggestedAlias(ImmutableDTO):
    """The model's alias of one item in one requested language."""

    item_id: KnowledgeItemId
    language: LanguageTag
    text: KnowledgeAliasText


class AliasSuggestionResult(ImmutableDTO):
    """
    The aliases the model suggested and what the call cost in tokens of
    `model_id`. An answer that is not the requested JSON is unreadable: no
    aliases, but its tokens were spent all the same.
    """

    is_answer_readable: IsAliasAnswerReadable = True
    aliases: list[SuggestedAlias] = Field(default_factory=list[SuggestedAlias])
    model_id: LlmModelId
    input_tokens: LlmTokenCount = LlmTokenCount(0)
    output_tokens: LlmTokenCount = LlmTokenCount(0)


class SuggestKnowledgeAliasesCommand(ImmutableDTO):
    """
    An owner asks for one item's aliases in the business's languages it
    still has none in; `language` formats the returned price.
    """

    user_id: UserId
    business_id: BusinessId
    item_id: KnowledgeItemId
    language: LanguageTag | None = None
