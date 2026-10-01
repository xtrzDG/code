from app.contracts.repositories import ResourceRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.resources import ResourceList, ResourceListQuery
from app.utilities.knowledge.resource_rules import resource_sort_key, to_resource_view


class ListResourcesUseCase(UseCaseContract[ResourceListQuery, ResourceList]):
    """List the resources of a business, optionally only active or inactive ones."""

    def __init__(self, resource_repo: ResourceRepoContract) -> None:
        self._resource_repo: ResourceRepoContract = resource_repo

    def run(self, input_data: ResourceListQuery) -> ResourceList:
        resources: list[ResourceDocument] = [
            resource
            for resource in self._resource_repo.list_by_business(input_data.business_id)
            if input_data.is_active is None
            or resource.is_active == input_data.is_active
        ]
        return ResourceList(
            items=[
                to_resource_view(resource)
                for resource in sorted(resources, key=resource_sort_key)
            ]
        )
