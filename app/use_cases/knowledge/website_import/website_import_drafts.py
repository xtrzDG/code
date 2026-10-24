"""
The knowledge drafts of one website import: switched off, in the import's
batch, with the page they came from, and each fact once (the opening hours
in every page's footer become one draft).
"""

import re
from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.schemas.constants.knowledge import KnowledgeItemKind, KnowledgeItemSource
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeAttribute, KnowledgeItemDocument
from app.schemas.dto.menu_import import ExtractedMenuItem
from app.schemas.typings.knowledge.strings import KnowledgeAttributeValue
from app.schemas.typings.menu_import.prefixed_id import MenuImportBatchId
from app.schemas.typings.web_fetching.constrained_strings import WebResourceUrl
from app.utilities.knowledge.imported_drafts import build_draft
from app.utilities.knowledge.imported_item_views import SOURCE_PAGE_ATTRIBUTE

MAX_DRAFTS_PER_IMPORT: int = 300
NOT_A_WORD: re.Pattern[str] = re.compile(r"[\W_]+")


class WebsiteImportDrafts:
    """Saves the drafts of one import, each fact once, at most 300."""

    def __init__(
        self,
        knowledge_item_repo: KnowledgeItemRepoContract,
        business: BusinessDocument,
        batch_id: MenuImportBatchId,
    ) -> None:
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._business: BusinessDocument = business
        self._batch_id: MenuImportBatchId = batch_id
        self._seen: set[tuple[KnowledgeItemKind, str]] = set()
        self._saved_count: int = 0

    def discard_earlier_attempt(self) -> None:
        """Delete drafts an interrupted run of this import left behind."""

        for item in self._knowledge_item_repo.list_by_business(self._business.id):
            if (
                item.import_batch_id == self._batch_id
                and item.source is KnowledgeItemSource.MENU_IMPORT
                and not item.is_active
            ):
                self._knowledge_item_repo.delete(self._business.id, item.id)

    def add(
        self,
        items: Sequence[ExtractedMenuItem],
        page_url: WebResourceUrl,
        now: Microseconds,
    ) -> int:
        """Save the page's new facts; how many were saved."""

        saved: int = 0
        for extracted in items:
            key: tuple[KnowledgeItemKind, str] = (
                extracted.kind,
                NOT_A_WORD.sub("", str(extracted.title).casefold()),
            )
            if key in self._seen or self._saved_count >= MAX_DRAFTS_PER_IMPORT:
                continue

            self._seen.add(key)
            draft: KnowledgeItemDocument = build_draft(
                self._business, extracted, self._batch_id, now
            )
            # Drafts keep the order they were found in (one microsecond apart).
            draft.created_at = Microseconds(int(now) + self._saved_count)
            draft.attributes.append(
                KnowledgeAttribute(
                    key=SOURCE_PAGE_ATTRIBUTE,
                    value=KnowledgeAttributeValue(str(page_url)),
                )
            )
            self._knowledge_item_repo.save(draft)
            self._saved_count += 1
            saved += 1

        return saved
