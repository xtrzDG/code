from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.storage import StorageScopeContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.brands.brand_commands import BrandQuery
from app.schemas.dto.brands.brand_knowledge import (
    BrandKnowledgeList,
    LocationOverrides,
    LocationOverridesQuery,
)
from app.schemas.dto.brands.brand_views import BrandView
from app.schemas.exceptions.application_errors import AccessDeniedError, NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.constrained_strings import KnowledgeShareKey


class BrandKnowledgeOrchestrator(OrchestratorContract[BrandQuery, BrandKnowledgeList]):
    """
    GET /v1/brands/{brand_id}/knowledge: the brand's shared facts, each
    with the locations (of those the member reaches) that replace it with
    their own item. Each location is read inside its own storage scope by
    a use case that checks the member's access to it again; one the
    member's session may not open (two factors) is left out of the marks.
    """

    def __init__(
        self,
        get_brand: UseCaseContract[BrandQuery, BrandView],
        list_knowledge: UseCaseContract[BrandQuery, BrandKnowledgeList],
        list_overrides: UseCaseContract[LocationOverridesQuery, LocationOverrides],
        storage_scope: StorageScopeContract,
    ) -> None:
        self._get_brand: UseCaseContract[BrandQuery, BrandView] = get_brand
        self._list_knowledge: UseCaseContract[BrandQuery, BrandKnowledgeList] = (
            list_knowledge
        )
        self._list_overrides: UseCaseContract[
            LocationOverridesQuery, LocationOverrides
        ] = list_overrides
        self._storage_scope: StorageScopeContract = storage_scope

    def execute(self, input_data: BrandQuery) -> BrandKnowledgeList:
        brand: BrandView = self._get_brand.run(input_data)
        knowledge: BrandKnowledgeList = self._list_knowledge.run(input_data)
        replaced_in: dict[KnowledgeShareKey, list[BusinessId]] = {}
        for location in brand.locations:
            try:
                with self._storage_scope.scoped_to_business(location.business_id):
                    overrides: LocationOverrides = self._list_overrides.run(
                        LocationOverridesQuery(
                            user_id=input_data.user_id,
                            business_id=location.business_id,
                        )
                    )
            except AccessDeniedError, NotFoundError:
                continue

            for key in overrides.shared_keys:
                replaced_in.setdefault(key, []).append(location.business_id)

        return BrandKnowledgeList(
            items=[
                item.model_copy(
                    update={"overridden_in": replaced_in.get(item.shared_key, [])}
                )
                for item in knowledge.items
            ]
        )
