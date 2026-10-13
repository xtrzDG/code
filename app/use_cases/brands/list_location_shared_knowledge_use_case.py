from app.contracts.repositories.brand_repositories import (
    BrandKnowledgeItemRepoContract,
)
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.brands import BrandKnowledgeItemDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.brands.brand_knowledge import (
    LocationOverridesQuery,
    LocationSharedItemView,
    LocationSharedKnowledge,
)
from app.schemas.typings.knowledge.constrained_strings import KnowledgeShareKey
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId


class ListLocationSharedKnowledgeUseCase(
    UseCaseContract[LocationOverridesQuery, LocationSharedKnowledge]
):
    """
    A location's knowledge page: the facts its brand shares, oldest first,
    each with the location's own item that replaces it there, if any (the
    team replaces one with POST .../knowledge/brand-overrides and edits it
    like any item). For everyone who reaches the location, its own team
    included; a business outside any brand has none.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        brand_knowledge_item_repo: BrandKnowledgeItemRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._brand_knowledge_item_repo: BrandKnowledgeItemRepoContract = (
            brand_knowledge_item_repo
        )
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo

    def run(self, input_data: LocationOverridesQuery) -> LocationSharedKnowledge:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        if business.brand_id is None:
            return LocationSharedKnowledge(business_id=business.id)

        shared: list[BrandKnowledgeItemDocument] = (
            self._brand_knowledge_item_repo.list_by_brand(business.brand_id)
        )
        own: dict[KnowledgeShareKey, KnowledgeItemId] = {}
        for item in self._knowledge_item_repo.list_by_business(business.id):
            if item.shared_key is not None:
                own.setdefault(item.shared_key, item.id)

        return LocationSharedKnowledge(
            business_id=business.id,
            brand_id=business.brand_id,
            items=[
                LocationSharedItemView(
                    shared_key=item.shared_key,
                    kind=item.kind,
                    title=item.title,
                    body=item.body,
                    price_minor=item.price_minor,
                    currency_code=item.currency_code,
                    is_active=item.is_active,
                    own_item_id=own.get(item.shared_key),
                )
                for item in shared
            ],
        )
