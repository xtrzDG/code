"""In-memory brand repositories for tests that build use cases by hand."""

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.brand_repositories import (
    BrandKnowledgeItemRepository,
    BrandRepository,
)
from app.schemas.domain.brands import BrandDocument, BrandKnowledgeItemDocument


def in_memory_brand_repo() -> BrandRepository:
    return BrandRepository(
        InMemoryDocumentCollectionAdapter[BrandDocument](BrandDocument)
    )


def in_memory_brand_knowledge_repo() -> BrandKnowledgeItemRepository:
    return BrandKnowledgeItemRepository(
        InMemoryDocumentCollectionAdapter[BrandKnowledgeItemDocument](
            BrandKnowledgeItemDocument
        )
    )
