from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.privacy import KnowledgeMentionMatch
from app.schemas.domain.knowledge import KnowledgeAlias, KnowledgeAttribute
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle


class KnowledgeMention(ImmutableDTO):
    """
    A knowledge item that mentions a customer (PRIV-08): by their name, by
    one of their numbers, or both (`matched_on`). The customer's export
    lists it with every text that was searched (title, body, attribute
    values and aliases), so the mention itself is in the copy; their
    erasure flags it for the owner's review and leaves the text as the
    owner wrote it.
    """

    knowledge_item_id: KnowledgeItemId
    title: KnowledgeTitle
    body: KnowledgeBody | None = None
    attributes: list[KnowledgeAttribute] = Field(
        default_factory=list[KnowledgeAttribute]
    )
    aliases: list[KnowledgeAlias] = Field(default_factory=list[KnowledgeAlias])
    matched_on: list[KnowledgeMentionMatch] = Field(
        default_factory=list[KnowledgeMentionMatch], min_length=1
    )
