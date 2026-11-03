from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.privacy import KnowledgeMentionMatch
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle


class KnowledgeMention(ImmutableDTO):
    """
    A knowledge item that mentions a customer (PRIV-08): by their name, by
    one of their numbers, or both (`matched_on`). The customer's export
    lists it with its text; their erasure flags it for the owner's review
    and leaves the text as the owner wrote it.
    """

    knowledge_item_id: KnowledgeItemId
    title: KnowledgeTitle
    body: KnowledgeBody | None = None
    matched_on: list[KnowledgeMentionMatch] = Field(
        default_factory=list[KnowledgeMentionMatch], min_length=1
    )
