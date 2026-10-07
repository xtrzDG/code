from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.growth_pipelines import GrowthPipelinesContainer
from app.containers.provider_chains import (
    pipeline_operator,
    platform_pipeline_operator,
)
from app.containers.utilities import UtilitiesContainer


class GrowthOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the waitlist and the rebooking campaigns: the hold expiry
    and the hourly campaigns run over every business (platform-wide); the
    offer job and the cabinet's endpoints in their business's scope.
    """

    growth_pipelines: GrowthPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    offer_freed_place_operator = pipeline_operator(
        growth_pipelines.offer_freed_place_pipeline, storage_scope
    )
    expire_waitlist_offers_operator = platform_pipeline_operator(
        growth_pipelines.expire_waitlist_offers_pipeline, storage_scope
    )
    list_waitlist_operator = pipeline_operator(
        growth_pipelines.list_waitlist_pipeline, storage_scope
    )
    remove_waitlist_entry_operator = pipeline_operator(
        growth_pipelines.remove_waitlist_entry_pipeline, storage_scope
    )
    get_waitlist_settings_operator = pipeline_operator(
        growth_pipelines.get_waitlist_settings_pipeline, storage_scope
    )
    update_waitlist_settings_operator = pipeline_operator(
        growth_pipelines.update_waitlist_settings_pipeline, storage_scope
    )
    run_rebooking_campaigns_operator = platform_pipeline_operator(
        growth_pipelines.run_rebooking_campaigns_pipeline, storage_scope
    )
    get_campaign_settings_operator = pipeline_operator(
        growth_pipelines.get_campaign_settings_pipeline, storage_scope
    )
    update_campaign_settings_operator = pipeline_operator(
        growth_pipelines.update_campaign_settings_pipeline, storage_scope
    )
    list_campaign_messages_operator = pipeline_operator(
        growth_pipelines.list_campaign_messages_pipeline, storage_scope
    )
