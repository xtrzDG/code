"""Frequent questions of the profile as knowledge items."""

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.dto.knowledge_admin import KnowledgeItemUpsertInput
from app.schemas.dto.profiles.business_profile import FaqEntryInput


def faq_entry_to_upsert_input(entry: FaqEntryInput) -> KnowledgeItemUpsertInput:
    """A frequent question as a FAQ knowledge item (question as the title)."""

    return KnowledgeItemUpsertInput(
        id=entry.id,
        kind=KnowledgeItemKind.FAQ,
        title=entry.question,
        body=entry.answer,
        languages=list(entry.languages),
    )
