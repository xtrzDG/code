from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.knowledge_repositories import ResourceRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.resources import ResourceView, UpdateResourceCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.utilities.knowledge.resource_rules import patch_resource, to_resource_view


class UpdateResourceUseCase(UseCaseContract[UpdateResourceCommand, ResourceView]):
    """
    Change a resource of the business or switch it off (`is_active`).

    Resources are not deleted, so past bookings keep their resource. A
    resource of another business is reported as missing.
    """

    def __init__(
        self,
        resource_repo: ResourceRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._resource_repo: ResourceRepoContract = resource_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: UpdateResourceCommand) -> ResourceView:
        existing: ResourceDocument | None = self._resource_repo.get(
            input_data.business_id,
            input_data.resource_id,
        )
        if existing is None:
            raise NotFoundError(f"Resource {input_data.resource_id} was not found.")

        updated: ResourceDocument = patch_resource(
            existing=existing,
            patch=input_data.patch,
            other_resources=[
                resource
                for resource in self._resource_repo.list_by_business(
                    input_data.business_id
                )
                if resource.id != existing.id
            ],
            now=self._wall_clock.now_unix(),
        )
        self._resource_repo.save(updated)
        return to_resource_view(updated)
