from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.campaign_use_cases import CampaignUseCasesContainer
from app.containers.use_cases.deposit_use_cases import DepositUseCasesContainer
from app.containers.use_cases.waitlist_use_cases import WaitlistUseCasesContainer


class GrowthOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators of the revenue features (1151): the waitlist's offer job
    and hold expiry, Bookings → Waitlist; the rebooking campaigns' hourly
    job and Bookings → Return visits; deposits (1190): their settings,
    "Paid", the report and the minute's sweep (one use case each).
    """

    waitlist_use_cases: WaitlistUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    campaign_use_cases: CampaignUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    deposit_use_cases: DepositUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    offer_freed_place_orchestrator = use_case_orchestrator(
        waitlist_use_cases.offer_freed_place_use_case
    )
    expire_waitlist_offers_orchestrator = use_case_orchestrator(
        waitlist_use_cases.expire_waitlist_offers_use_case
    )
    list_waitlist_orchestrator = use_case_orchestrator(
        waitlist_use_cases.list_waitlist_use_case
    )
    remove_waitlist_entry_orchestrator = use_case_orchestrator(
        waitlist_use_cases.remove_waitlist_entry_use_case
    )
    get_waitlist_settings_orchestrator = use_case_orchestrator(
        waitlist_use_cases.get_waitlist_settings_use_case
    )
    update_waitlist_settings_orchestrator = use_case_orchestrator(
        waitlist_use_cases.update_waitlist_settings_use_case
    )
    run_rebooking_campaigns_orchestrator = use_case_orchestrator(
        campaign_use_cases.run_rebooking_campaigns_use_case
    )
    get_campaign_settings_orchestrator = use_case_orchestrator(
        campaign_use_cases.get_campaign_settings_use_case
    )
    update_campaign_settings_orchestrator = use_case_orchestrator(
        campaign_use_cases.update_campaign_settings_use_case
    )
    list_campaign_messages_orchestrator = use_case_orchestrator(
        campaign_use_cases.list_campaign_messages_use_case
    )
    # Deposits and prepayment links (1190), one use case each.
    get_deposit_settings_orchestrator = use_case_orchestrator(
        deposit_use_cases.get_deposit_settings_use_case
    )
    update_deposit_settings_orchestrator = use_case_orchestrator(
        deposit_use_cases.update_deposit_settings_use_case
    )
    add_payment_link_orchestrator = use_case_orchestrator(
        deposit_use_cases.add_payment_link_use_case
    )
    remove_payment_link_orchestrator = use_case_orchestrator(
        deposit_use_cases.remove_payment_link_use_case
    )
    set_deposit_policy_orchestrator = use_case_orchestrator(
        deposit_use_cases.set_deposit_policy_use_case
    )
    get_deposit_request_orchestrator = use_case_orchestrator(
        deposit_use_cases.get_deposit_request_use_case
    )
    mark_deposit_paid_orchestrator = use_case_orchestrator(
        deposit_use_cases.mark_deposit_paid_use_case
    )
    get_deposit_report_orchestrator = use_case_orchestrator(
        deposit_use_cases.get_deposit_report_use_case
    )
    sweep_deposits_orchestrator = use_case_orchestrator(
        deposit_use_cases.sweep_deposits_use_case
    )
