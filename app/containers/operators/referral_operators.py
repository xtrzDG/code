from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.referral_pipelines import ReferralPipelinesContainer
from app.containers.provider_chains import (
    pipeline_operator,
    platform_pipeline_operator,
)
from app.containers.utilities import UtilitiesContainer


class ReferralOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the referral program's endpoints. An owner's invitation
    runs in the business's scope; a partner's portal and the admin's
    partners and payouts read across businesses (the businesses a partner
    brought, their commissions), so they run platform-wide.
    """

    referral_pipelines: ReferralPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    get_referral_program_operator = pipeline_operator(
        referral_pipelines.get_referral_program_pipeline, storage_scope
    )
    set_powered_by_operator = pipeline_operator(
        referral_pipelines.set_powered_by_pipeline, storage_scope
    )
    get_partner_portal_operator = platform_pipeline_operator(
        referral_pipelines.get_partner_portal_pipeline, storage_scope
    )
    list_partner_referrals_operator = platform_pipeline_operator(
        referral_pipelines.list_partner_referrals_pipeline, storage_scope
    )
    list_partner_commissions_operator = platform_pipeline_operator(
        referral_pipelines.list_partner_commissions_pipeline, storage_scope
    )
    list_partners_operator = platform_pipeline_operator(
        referral_pipelines.list_partners_pipeline, storage_scope
    )
    create_partner_operator = platform_pipeline_operator(
        referral_pipelines.create_partner_pipeline, storage_scope
    )
    update_partner_operator = platform_pipeline_operator(
        referral_pipelines.update_partner_pipeline, storage_scope
    )
    add_partner_code_operator = platform_pipeline_operator(
        referral_pipelines.add_partner_code_pipeline, storage_scope
    )
    get_payout_report_operator = platform_pipeline_operator(
        referral_pipelines.get_payout_report_pipeline, storage_scope
    )
    mark_payout_paid_operator = platform_pipeline_operator(
        referral_pipelines.mark_payout_paid_pipeline, storage_scope
    )
