from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.growth_orchestrators import (
    GrowthOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class GrowthPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of the waitlist and the rebooking campaigns."""

    growth: GrowthOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    offer_freed_place_pipeline = orchestrator_pipeline(
        growth.offer_freed_place_orchestrator
    )
    expire_waitlist_offers_pipeline = orchestrator_pipeline(
        growth.expire_waitlist_offers_orchestrator
    )
    list_waitlist_pipeline = orchestrator_pipeline(growth.list_waitlist_orchestrator)
    remove_waitlist_entry_pipeline = orchestrator_pipeline(
        growth.remove_waitlist_entry_orchestrator
    )
    get_waitlist_settings_pipeline = orchestrator_pipeline(
        growth.get_waitlist_settings_orchestrator
    )
    update_waitlist_settings_pipeline = orchestrator_pipeline(
        growth.update_waitlist_settings_orchestrator
    )
    run_rebooking_campaigns_pipeline = orchestrator_pipeline(
        growth.run_rebooking_campaigns_orchestrator
    )
    get_campaign_settings_pipeline = orchestrator_pipeline(
        growth.get_campaign_settings_orchestrator
    )
    update_campaign_settings_pipeline = orchestrator_pipeline(
        growth.update_campaign_settings_orchestrator
    )
    list_campaign_messages_pipeline = orchestrator_pipeline(
        growth.list_campaign_messages_orchestrator
    )
