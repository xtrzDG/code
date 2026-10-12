from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.growth_orchestrators import (
    GrowthOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class GrowthPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of the waitlist, the rebooking campaigns and the deposits."""

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
    get_deposit_settings_pipeline = orchestrator_pipeline(
        growth.get_deposit_settings_orchestrator
    )
    update_deposit_settings_pipeline = orchestrator_pipeline(
        growth.update_deposit_settings_orchestrator
    )
    add_payment_link_pipeline = orchestrator_pipeline(
        growth.add_payment_link_orchestrator
    )
    remove_payment_link_pipeline = orchestrator_pipeline(
        growth.remove_payment_link_orchestrator
    )
    set_deposit_policy_pipeline = orchestrator_pipeline(
        growth.set_deposit_policy_orchestrator
    )
    get_deposit_request_pipeline = orchestrator_pipeline(
        growth.get_deposit_request_orchestrator
    )
    mark_deposit_paid_pipeline = orchestrator_pipeline(
        growth.mark_deposit_paid_orchestrator
    )
    get_deposit_report_pipeline = orchestrator_pipeline(
        growth.get_deposit_report_orchestrator
    )
    sweep_deposits_pipeline = orchestrator_pipeline(growth.sweep_deposits_orchestrator)
