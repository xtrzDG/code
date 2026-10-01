from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import NicheTemplateRegistryContract
from app.contracts.repositories import BusinessRepoContract, ResourceRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.resources import CreateResourceCommand, ResourceView
from app.schemas.exceptions.application_errors import NotFoundError
from app.utilities.knowledge.resource_rules import build_resource, to_resource_view


class CreateResourceUseCase(UseCaseContract[CreateResourceCommand, ResourceView]):
    """
    Add something bookable: a table, a room type, a master, an arena, a car.

    Kind and booking unit default to the niche (hotels and rentals book by
    nights). Names are unique within the business; an own schedule must not
    overlap itself, and an empty one follows the business hours.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        resource_repo: ResourceRepoContract,
        niche_template_registry: NicheTemplateRegistryContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._niche_template_registry: NicheTemplateRegistryContract = (
            niche_template_registry
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CreateResourceCommand) -> ResourceView:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        resource: ResourceDocument = build_resource(
            business=business,
            template=self._niche_template_registry.get(business.niche_key),
            resource_input=input_data.resource,
            existing_resources=self._resource_repo.list_by_business(business.id),
            now=self._wall_clock.now_unix(),
        )
        self._resource_repo.save(resource)
        return to_resource_view(resource)
