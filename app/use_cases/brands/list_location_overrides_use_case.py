from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.brands.brand_knowledge import (
    LocationOverrides,
    LocationOverridesQuery,
)
from app.schemas.typings.knowledge.constrained_strings import KnowledgeShareKey


class ListLocationOverridesUseCase(
    UseCaseContract[LocationOverridesQuery, LocationOverrides]
):
    """
    The shared facts one location replaces with its own items (their
    keys), for a member who reaches the location (checked here again).
    Runs in the location's storage scope.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        knowledge_item_repo: KnowledgeItemRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo

    def run(self, input_data: LocationOverridesQuery) -> LocationOverrides:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        keys: list[KnowledgeShareKey] = [
            item.shared_key
            for item in self._knowledge_item_repo.list_by_business(business.id)
            if item.shared_key is not None
        ]
        return LocationOverrides(
            business_id=business.id, shared_keys=list(dict.fromkeys(keys))
        )
