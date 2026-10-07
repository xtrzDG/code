from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.referral_orchestrators import (
    ReferralOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class ReferralPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of the referral program's endpoints."""

    referrals: ReferralOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    get_referral_program_pipeline = orchestrator_pipeline(
        referrals.get_referral_program_orchestrator
    )
    set_powered_by_pipeline = orchestrator_pipeline(
        referrals.set_powered_by_orchestrator
    )
    get_partner_portal_pipeline = orchestrator_pipeline(
        referrals.get_partner_portal_orchestrator
    )
    list_partner_referrals_pipeline = orchestrator_pipeline(
        referrals.list_partner_referrals_orchestrator
    )
    list_partner_commissions_pipeline = orchestrator_pipeline(
        referrals.list_partner_commissions_orchestrator
    )
    list_partners_pipeline = orchestrator_pipeline(referrals.list_partners_orchestrator)
    create_partner_pipeline = orchestrator_pipeline(
        referrals.create_partner_orchestrator
    )
    update_partner_pipeline = orchestrator_pipeline(
        referrals.update_partner_orchestrator
    )
    add_partner_code_pipeline = orchestrator_pipeline(
        referrals.add_partner_code_orchestrator
    )
    get_payout_report_pipeline = orchestrator_pipeline(
        referrals.get_payout_report_orchestrator
    )
    mark_payout_paid_pipeline = orchestrator_pipeline(
        referrals.mark_payout_paid_orchestrator
    )
