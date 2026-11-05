from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.referral_use_cases import ReferralUseCasesContainer


class ReferralOrchestratorsContainer(containers.DeclarativeContainer):
    """Orchestrators of the referral program's endpoints (one use case each)."""

    referral_use_cases: ReferralUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    get_referral_program_orchestrator = use_case_orchestrator(
        referral_use_cases.get_referral_program_use_case
    )
    set_powered_by_orchestrator = use_case_orchestrator(
        referral_use_cases.set_powered_by_use_case
    )
    get_partner_portal_orchestrator = use_case_orchestrator(
        referral_use_cases.get_partner_portal_use_case
    )
    list_partner_referrals_orchestrator = use_case_orchestrator(
        referral_use_cases.list_partner_referrals_use_case
    )
    list_partner_commissions_orchestrator = use_case_orchestrator(
        referral_use_cases.list_partner_commissions_use_case
    )
    list_partners_orchestrator = use_case_orchestrator(
        referral_use_cases.list_partners_use_case
    )
    create_partner_orchestrator = use_case_orchestrator(
        referral_use_cases.create_partner_use_case
    )
    update_partner_orchestrator = use_case_orchestrator(
        referral_use_cases.update_partner_use_case
    )
    add_partner_code_orchestrator = use_case_orchestrator(
        referral_use_cases.add_partner_code_use_case
    )
    get_payout_report_orchestrator = use_case_orchestrator(
        referral_use_cases.get_payout_report_use_case
    )
    mark_payout_paid_orchestrator = use_case_orchestrator(
        referral_use_cases.mark_payout_paid_use_case
    )
