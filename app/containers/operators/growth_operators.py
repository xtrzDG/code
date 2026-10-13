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
    Operators of the waitlist, the rebooking campaigns and the deposits: the
    hold expiry, the hourly campaigns and the deposits' sweep run over every
    business (platform-wide); the offer job and the cabinet's endpoints in
    their business's scope.
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
    get_deposit_settings_operator = pipeline_operator(
        growth_pipelines.get_deposit_settings_pipeline, storage_scope
    )
    update_deposit_settings_operator = pipeline_operator(
        growth_pipelines.update_deposit_settings_pipeline, storage_scope
    )
    add_payment_link_operator = pipeline_operator(
        growth_pipelines.add_payment_link_pipeline, storage_scope
    )
    remove_payment_link_operator = pipeline_operator(
        growth_pipelines.remove_payment_link_pipeline, storage_scope
    )
    set_deposit_policy_operator = pipeline_operator(
        growth_pipelines.set_deposit_policy_pipeline, storage_scope
    )
    get_deposit_request_operator = pipeline_operator(
        growth_pipelines.get_deposit_request_pipeline, storage_scope
    )
    mark_deposit_paid_operator = pipeline_operator(
        growth_pipelines.mark_deposit_paid_pipeline, storage_scope
    )
    get_deposit_report_operator = pipeline_operator(
        growth_pipelines.get_deposit_report_pipeline, storage_scope
    )
    sweep_deposits_operator = platform_pipeline_operator(
        growth_pipelines.sweep_deposits_pipeline, storage_scope
    )
