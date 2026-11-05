"""The cabinet's view of a website import, with its drafts once it is done."""

from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.schemas.constants.knowledge import KnowledgeItemSource
from app.schemas.constants.website_import import WebsiteImportStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.website_imports import WebsiteImportDocument
from app.schemas.dto.menu_import import MenuImportResult
from app.schemas.dto.website_import import WebsiteImportView
from app.utilities.knowledge.imported_item_views import build_imported_item_view


def build_website_import_view(
    website_import: WebsiteImportDocument,
    result: MenuImportResult | None = None,
) -> WebsiteImportView:
    return WebsiteImportView(
        id=website_import.import_id,
        business_id=website_import.business_id,
        status=website_import.status,
        url=website_import.url,
        pages_planned=website_import.pages_planned,
        pages_read=website_import.pages_read,
        pages_skipped=website_import.pages_skipped,
        items_found=website_import.items_found,
        problem=website_import.problem,
        problem_detail=website_import.problem_detail,
        started_at=website_import.started_at,
        finished_at=website_import.finished_at,
        result=result,
    )


def list_waiting_drafts(
    knowledge_item_repo: KnowledgeItemRepoContract,
    website_import: WebsiteImportDocument,
) -> list[KnowledgeItemDocument]:
    """The import's drafts not yet confirmed or discarded, in the order found."""

    return sorted(
        (
            item
            for item in knowledge_item_repo.list_by_business(website_import.business_id)
            if item.import_batch_id == website_import.batch_id
            and item.source is KnowledgeItemSource.MENU_IMPORT
            and not item.is_active
        ),
        key=lambda item: item.created_at,
    )


def build_import_result(
    business: BusinessDocument,
    website_import: WebsiteImportDocument,
    knowledge_item_repo: KnowledgeItemRepoContract,
) -> MenuImportResult | None:
    """The drafts waiting for review, once the import is done."""

    if website_import.status is not WebsiteImportStatus.DONE:
        return None

    return MenuImportResult(
        business_id=business.id,
        batch_id=website_import.batch_id,
        items=[
            build_imported_item_view(draft, business.owner_language)
            for draft in list_waiting_drafts(knowledge_item_repo, website_import)
        ],
        skipped_line_count=website_import.skipped_line_count,
    )
