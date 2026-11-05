from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.storage import StorageScopeContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.brands.brand_commands import CloneBrandLocationCommand
from app.schemas.dto.brands.location_templates import (
    ClonedLocationRequest,
    LocationTemplate,
    LocationTemplateQuery,
    LocationTemplateWrite,
)
from app.schemas.dto.businesses import BusinessQuery, BusinessView


class CloneBrandLocationOrchestrator(
    OrchestratorContract[CloneBrandLocationCommand, BusinessView]
):
    """
    POST /v1/brands/{brand_id}/locations/clone, "New location from…": a
    brand owner opens a new location of the brand from one of its
    locations. The source's profile, resources, knowledge and channel
    settings are read inside its storage scope (never its channel tokens,
    billing, API keys, webhooks or customers), the new business is created
    in the brand with the brand owner as its owner, and the copies are
    written inside the new location's scope. Answers the new business.
    """

    def __init__(
        self,
        authorize_clone: UseCaseContract[CloneBrandLocationCommand, BusinessDocument],
        read_template: UseCaseContract[LocationTemplateQuery, LocationTemplate],
        create_location: UseCaseContract[ClonedLocationRequest, BusinessDocument],
        write_template: UseCaseContract[LocationTemplateWrite, None],
        get_business: UseCaseContract[BusinessQuery, BusinessView],
        storage_scope: StorageScopeContract,
    ) -> None:
        self._authorize_clone: UseCaseContract[
            CloneBrandLocationCommand, BusinessDocument
        ] = authorize_clone
        self._read_template: UseCaseContract[
            LocationTemplateQuery, LocationTemplate
        ] = read_template
        self._create_location: UseCaseContract[
            ClonedLocationRequest, BusinessDocument
        ] = create_location
        self._write_template: UseCaseContract[LocationTemplateWrite, None] = (
            write_template
        )
        self._get_business: UseCaseContract[BusinessQuery, BusinessView] = get_business
        self._storage_scope: StorageScopeContract = storage_scope

    def execute(self, input_data: CloneBrandLocationCommand) -> BusinessView:
        source: BusinessDocument = self._authorize_clone.run(input_data)
        with self._storage_scope.scoped_to_business(source.id):
            template: LocationTemplate = self._read_template.run(
                LocationTemplateQuery(user_id=input_data.user_id, business_id=source.id)
            )

        created: BusinessDocument = self._create_location.run(
            ClonedLocationRequest(
                user_id=input_data.user_id,
                brand_id=input_data.brand_id,
                source=source,
                name=input_data.request.name,
                city=input_data.request.city,
                client_ip_address=input_data.client_ip_address,
            )
        )
        with self._storage_scope.scoped_to_business(created.id):
            self._write_template.run(
                LocationTemplateWrite(
                    user_id=input_data.user_id,
                    business_id=created.id,
                    template=template,
                )
            )
            return self._get_business.run(
                BusinessQuery(user_id=input_data.user_id, business_id=created.id)
            )
