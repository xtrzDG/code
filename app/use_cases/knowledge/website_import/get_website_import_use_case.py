from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.contracts.repositories.website_import_repositories import (
    WebsiteImportRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.website_imports import WebsiteImportDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.website_import import CurrentWebsiteImport, GetWebsiteImportQuery
from app.use_cases.knowledge.website_import.website_import_views import (
    build_import_result,
    build_website_import_view,
)


class GetWebsiteImportUseCase(
    UseCaseContract[GetWebsiteImportQuery, CurrentWebsiteImport]
):
    """
    The business's current website import (owners and staff): how far the
    worker got, why it failed, and, once it is done, the drafts still
    waiting for review in the same shape as a menu import.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        website_import_repo: WebsiteImportRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._website_import_repo: WebsiteImportRepoContract = website_import_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo

    def run(self, input_data: GetWebsiteImportQuery) -> CurrentWebsiteImport:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        website_import: WebsiteImportDocument | None = (
            self._website_import_repo.get_by_business(business.id)
        )
        if website_import is None:
            return CurrentWebsiteImport()

        return CurrentWebsiteImport(
            current=build_website_import_view(
                website_import,
                build_import_result(
                    business, website_import, self._knowledge_item_repo
                ),
            )
        )
