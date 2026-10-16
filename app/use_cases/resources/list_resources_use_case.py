from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.resources import ResourceList, ResourceListQuery
from app.utilities.knowledge.resource_rules import resource_sort_key, to_resource_view


class ListResourcesUseCase(UseCaseContract[ResourceListQuery, ResourceList]):
    """
    List the resources of a business, optionally only active or inactive
    ones, each with the services it performs (linked from either side).
    """

    def __init__(
        self,
        resource_repo: ResourceRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
    ) -> None:
        self._resource_repo: ResourceRepoContract = resource_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo

    def run(self, input_data: ResourceListQuery) -> ResourceList:
        resources: list[ResourceDocument] = [
            resource
            for resource in self._resource_repo.list_by_business(input_data.business_id)
            if input_data.is_active is None
            or resource.is_active == input_data.is_active
        ]
        items: list[KnowledgeItemDocument] = self._knowledge_item_repo.list_by_business(
            input_data.business_id
        )
        return ResourceList(
            items=[
                to_resource_view(resource, items)
                for resource in sorted(resources, key=resource_sort_key)
            ]
        )
