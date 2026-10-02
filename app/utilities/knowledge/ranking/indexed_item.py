"""The search tokens of one knowledge item, by field, with field weights."""

from dataclasses import dataclass

from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.utilities.knowledge.search_text import SearchToken, tokenize, unique_tokens

TITLE_WEIGHT: float = 3.0
TAG_WEIGHT: float = 2.0
ATTRIBUTE_WEIGHT: float = 1.5
BODY_WEIGHT: float = 1.0


@dataclass(frozen=True)
class IndexedItem:
    """Tokens of one item, by field."""

    item: KnowledgeItemDocument
    title_tokens: list[SearchToken]
    tag_tokens: list[SearchToken]
    attribute_tokens: list[SearchToken]
    body_tokens: list[SearchToken]

    def fields(self) -> list[tuple[float, list[SearchToken]]]:
        return [
            (TITLE_WEIGHT, self.title_tokens),
            (TAG_WEIGHT, self.tag_tokens),
            (ATTRIBUTE_WEIGHT, self.attribute_tokens),
            (BODY_WEIGHT, self.body_tokens),
        ]


def index_item(item: KnowledgeItemDocument) -> IndexedItem:
    attribute_text: str = " ".join(
        f"{attribute.key} {attribute.value}" for attribute in item.attributes
    )
    return IndexedItem(
        item=item,
        title_tokens=unique_tokens(tokenize(item.title)),
        tag_tokens=unique_tokens(
            tokenize(" ".join(tag.replace("_", " ") for tag in item.tags))
        ),
        attribute_tokens=unique_tokens(tokenize(attribute_text.replace("_", " "))),
        body_tokens=unique_tokens(tokenize(item.body or "")),
    )
