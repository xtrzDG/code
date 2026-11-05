from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.facilitators import FacilitatorsContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.brands import BrandDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.brands.brand_commands import (
    BrandAccessRequest,
    BrandQuery,
    CloneBrandLocationCommand,
)
from app.schemas.dto.brands.brand_knowledge import (
    BrandKnowledgeCommand,
    BrandKnowledgeItemCommand,
    BrandKnowledgeItemView,
    BrandKnowledgeList,
    LocationOverrides,
    LocationOverridesQuery,
    LocationSharedKnowledge,
    OverrideBrandKnowledgeCommand,
)
from app.schemas.dto.brands.location_plans import LocationPlanQuery, LocationPricing
from app.schemas.dto.brands.location_templates import (
    ClonedLocationRequest,
    LocationTemplate,
    LocationTemplateQuery,
    LocationTemplateWrite,
)
from app.schemas.dto.knowledge_admin import KnowledgeItemDetails
from app.use_cases.brands import (
    authorize_brand_access_use_case as authorize,
)
from app.use_cases.brands import (
    authorize_location_clone_use_case as authorize_clone,
)
from app.use_cases.brands import (
    create_brand_knowledge_item_use_case as create_item,
)
from app.use_cases.brands import (
    create_cloned_location_use_case as create_location,
)
from app.use_cases.brands import (
    delete_brand_knowledge_item_use_case as delete_item,
)
from app.use_cases.brands import (
    describe_location_pricing_use_case as describe_pricing,
)
from app.use_cases.brands import (
    list_brand_knowledge_use_case as list_knowledge,
)
from app.use_cases.brands import (
    list_location_overrides_use_case as list_overrides,
)
from app.use_cases.brands import (
    list_location_shared_knowledge_use_case as list_location_shared,
)
from app.use_cases.brands import (
    override_brand_knowledge_use_case as override,
)
from app.use_cases.brands import (
    read_location_template_use_case as read_template,
)
from app.use_cases.brands import (
    update_brand_knowledge_item_use_case as update_item,
)
from app.use_cases.brands import (
    write_location_template_use_case as write_template,
)


class BrandContentUseCasesContainer(containers.DeclarativeContainer):
    """
    The edges of the brand use cases, the brand access check, the
    knowledge a brand's locations share (with each location's overrides)
    and "New location from…" (the template read from a location and
    written into a new one). `BrandUseCasesContainer` adds the brand, its
    locations and its team on top.
    """

    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    transformers: TransformersContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    repos = repositories
    clock = time_provider.microsecond_wall_clock
    views = transformers.brand_view_transformer
    business_access = account_use_cases.authorize_business_access_use_case

    authorize_brand_access_use_case: Factory[
        UseCaseContract[BrandAccessRequest, BrandDocument]
    ] = Factory(
        authorize.AuthorizeBrandAccessUseCase,
        brand_repo=repos.brand_repo,
        business_repo=repos.business_repo,
        session_assurance=utilities.session_assurance,
    )
    brand_access = authorize_brand_access_use_case

    list_brand_knowledge_use_case: Factory[
        UseCaseContract[BrandQuery, BrandKnowledgeList]
    ] = Factory(
        list_knowledge.ListBrandKnowledgeUseCase,
        authorize_brand_access=brand_access,
        brand_knowledge_item_repo=repos.brand_knowledge_item_repo,
    )
    create_brand_knowledge_item_use_case: Factory[
        UseCaseContract[BrandKnowledgeCommand, BrandKnowledgeItemView]
    ] = Factory(
        create_item.CreateBrandKnowledgeItemUseCase,
        authorize_brand_access=brand_access,
        brand_knowledge_item_repo=repos.brand_knowledge_item_repo,
        business_repo=repos.business_repo,
        wall_clock=clock,
    )
    update_brand_knowledge_item_use_case: Factory[
        UseCaseContract[BrandKnowledgeItemCommand, BrandKnowledgeItemView]
    ] = Factory(
        update_item.UpdateBrandKnowledgeItemUseCase,
        authorize_brand_access=brand_access,
        brand_knowledge_item_repo=repos.brand_knowledge_item_repo,
        business_repo=repos.business_repo,
        wall_clock=clock,
    )
    delete_brand_knowledge_item_use_case: Factory[
        UseCaseContract[BrandKnowledgeItemCommand, None]
    ] = Factory(
        delete_item.DeleteBrandKnowledgeItemUseCase,
        authorize_brand_access=brand_access,
        brand_knowledge_item_repo=repos.brand_knowledge_item_repo,
    )
    list_location_overrides_use_case: Factory[
        UseCaseContract[LocationOverridesQuery, LocationOverrides]
    ] = Factory(
        list_overrides.ListLocationOverridesUseCase,
        authorize_business_access=business_access,
        knowledge_item_repo=repos.knowledge_item_repo,
    )
    list_location_shared_knowledge_use_case: Factory[
        UseCaseContract[LocationOverridesQuery, LocationSharedKnowledge]
    ] = Factory(
        list_location_shared.ListLocationSharedKnowledgeUseCase,
        authorize_business_access=business_access,
        brand_knowledge_item_repo=repos.brand_knowledge_item_repo,
        knowledge_item_repo=repos.knowledge_item_repo,
    )
    describe_location_pricing_use_case: Factory[
        UseCaseContract[LocationPlanQuery, LocationPricing]
    ] = Factory(
        describe_pricing.DescribeLocationPricingUseCase,
        authorize_business_access=business_access,
        brand_repo=repos.brand_repo,
        business_repo=repos.business_repo,
    )
    override_brand_knowledge_use_case: Factory[
        UseCaseContract[OverrideBrandKnowledgeCommand, KnowledgeItemDetails]
    ] = Factory(
        override.OverrideBrandKnowledgeUseCase,
        authorize_business_access=business_access,
        brand_knowledge_item_repo=repos.brand_knowledge_item_repo,
        knowledge_item_repo=repos.knowledge_item_repo,
        wall_clock=clock,
    )
    authorize_location_clone_use_case: Factory[
        UseCaseContract[CloneBrandLocationCommand, BusinessDocument]
    ] = Factory(
        authorize_clone.AuthorizeLocationCloneUseCase,
        authorize_brand_access=brand_access,
        business_repo=repos.business_repo,
    )
    read_location_template_use_case: Factory[
        UseCaseContract[LocationTemplateQuery, LocationTemplate]
    ] = Factory(
        read_template.ReadLocationTemplateUseCase,
        authorize_business_access=business_access,
        business_profile_repo=repos.business_profile_repo,
        resource_repo=repos.resource_repo,
        knowledge_item_repo=repos.knowledge_item_repo,
        channel_repo=repos.channel_repo,
    )
    create_cloned_location_use_case: Factory[
        UseCaseContract[ClonedLocationRequest, BusinessDocument]
    ] = Factory(
        create_location.CreateClonedLocationUseCase,
        business_repo=repos.business_repo,
        audit_log_repo=repos.audit_log_repo,
        product_events=facilitators.product_events,
        wall_clock=clock,
    )
    write_location_template_use_case: Factory[
        UseCaseContract[LocationTemplateWrite, None]
    ] = Factory(
        write_template.WriteLocationTemplateUseCase,
        authorize_business_access=business_access,
        business_profile_repo=repos.business_profile_repo,
        resource_repo=repos.resource_repo,
        knowledge_item_repo=repos.knowledge_item_repo,
        channel_repo=repos.channel_repo,
        wall_clock=clock,
    )
