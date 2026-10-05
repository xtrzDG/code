from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.platform_use_cases import PlatformUseCasesContainer
from app.containers.use_cases.voice_use_cases import VoiceUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.admin import AdminClientQuery
from app.schemas.dto.admin_actions import (
    AdminActionReceipt,
    CompleteOnboardingCommand,
    ExtendTrialCommand,
    GiveDiscountCommand,
    GrantCreditCommand,
    MarkInvoicePaidCommand,
    OverridePlanCommand,
    WaiveSetupFeeCommand,
)
from app.schemas.dto.client_story import (
    ClientNoteList,
    ClientTimelinePage,
    ClientTimelineQuery,
    CreateClientNoteCommand,
    DeleteClientNoteCommand,
    UpdateClientNoteCommand,
)
from app.schemas.dto.jobs import JobReport, JobTick
from app.use_cases.admin.billing_actions.account_action_gate import AccountActionGate
from app.use_cases.admin.billing_actions.complete_onboarding_use_case import (
    CompleteOnboardingUseCase,
)
from app.use_cases.admin.billing_actions.extend_trial_use_case import (
    ExtendTrialUseCase,
)
from app.use_cases.admin.billing_actions.give_discount_use_case import (
    GiveDiscountUseCase,
)
from app.use_cases.admin.billing_actions.grant_credit_use_case import (
    GrantCreditUseCase,
)
from app.use_cases.admin.billing_actions.mark_invoice_paid_use_case import (
    MarkInvoicePaidUseCase,
)
from app.use_cases.admin.billing_actions.override_plan_use_case import (
    OverridePlanUseCase,
)
from app.use_cases.admin.billing_actions.waive_setup_fee_use_case import (
    WaiveSetupFeeUseCase,
)
from app.use_cases.admin.client_notes.client_note_board import ClientNoteBoard
from app.use_cases.admin.client_notes.create_client_note_use_case import (
    CreateClientNoteUseCase,
)
from app.use_cases.admin.client_notes.delete_client_note_use_case import (
    DeleteClientNoteUseCase,
)
from app.use_cases.admin.client_notes.list_client_notes_use_case import (
    ListClientNotesUseCase,
)
from app.use_cases.admin.client_notes.update_client_note_use_case import (
    UpdateClientNoteUseCase,
)
from app.use_cases.admin.digests.send_critical_clients_digest_use_case import (
    SendCriticalClientsDigestUseCase,
)
from app.use_cases.admin.timeline.get_client_timeline_use_case import (
    GetClientTimelineUseCase,
)


class AdminActionUseCasesContainer(containers.DeclarativeContainer):
    """
    The admin that acts (R13): account actions with a reason and an audit
    entry, the platform team's notes, a client's timeline and the daily
    digest of clients that newly turned critical.
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    platform_use_cases: PlatformUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    voice_use_cases: VoiceUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    wall_clock = time_provider.microsecond_wall_clock
    authorize = platform_use_cases.authorize_platform_admin_use_case

    # --- Account actions: BILLING or SUPER, a recent sign-in, a reason.
    account_action_gate: Factory[AccountActionGate] = Factory(
        AccountActionGate,
        authorize_platform_admin=authorize,
        business_repo=repositories.business_repo,
        subscription_repo=repositories.subscription_repo,
        audit_log_repo=repositories.audit_log_repo,
        step_up=utilities.step_up_guard,
        unit_of_work=adapters.storage_unit_of_work,
    )
    extend_trial_use_case: Factory[
        UseCaseContract[ExtendTrialCommand, AdminActionReceipt]
    ] = Factory(
        ExtendTrialUseCase,
        gate=account_action_gate,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        business_repo=repositories.business_repo,
        wall_clock=wall_clock,
    )
    give_discount_use_case: Factory[
        UseCaseContract[GiveDiscountCommand, AdminActionReceipt]
    ] = Factory(
        GiveDiscountUseCase,
        gate=account_action_gate,
        subscription_repo=repositories.subscription_repo,
        wall_clock=wall_clock,
    )
    grant_credit_use_case: Factory[
        UseCaseContract[GrantCreditCommand, AdminActionReceipt]
    ] = Factory(
        GrantCreditUseCase,
        gate=account_action_gate,
        billing_credit_repo=repositories.billing_credit_repo,
        wall_clock=wall_clock,
    )
    waive_setup_fee_use_case: Factory[
        UseCaseContract[WaiveSetupFeeCommand, AdminActionReceipt]
    ] = Factory(
        WaiveSetupFeeUseCase,
        gate=account_action_gate,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        wall_clock=wall_clock,
    )
    mark_invoice_paid_use_case: Factory[
        UseCaseContract[MarkInvoicePaidCommand, AdminActionReceipt]
    ] = Factory(
        MarkInvoicePaidUseCase,
        gate=account_action_gate,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        business_repo=repositories.business_repo,
        product_events=facilitators.product_events,
        wall_clock=wall_clock,
    )
    override_plan_use_case: Factory[
        UseCaseContract[OverridePlanCommand, AdminActionReceipt]
    ] = Factory(
        OverridePlanUseCase,
        gate=account_action_gate,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        business_repo=repositories.business_repo,
        plan_registry=registries.plan_registry,
        payment_gateway=adapters.payment_gateway,
        remove_voice_agent=voice_use_cases.remove_voice_agent_use_case,
        product_events=facilitators.product_events,
        wall_clock=wall_clock,
    )
    complete_onboarding_use_case: Factory[
        UseCaseContract[CompleteOnboardingCommand, AdminActionReceipt]
    ] = Factory(
        CompleteOnboardingUseCase,
        authorize_platform_admin=authorize,
        business_repo=repositories.business_repo,
        onboarding_request_repo=repositories.onboarding_request_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=wall_clock,
    )

    # --- The platform team's notes and the client's story.
    client_note_board: Factory[ClientNoteBoard] = Factory(
        ClientNoteBoard,
        authorize_platform_admin=authorize,
        business_repo=repositories.business_repo,
        client_note_repo=repositories.client_note_repo,
        user_repo=repositories.user_repo,
    )
    list_client_notes_use_case: Factory[
        UseCaseContract[AdminClientQuery, ClientNoteList]
    ] = Factory(ListClientNotesUseCase, board=client_note_board)
    create_client_note_use_case: Factory[
        UseCaseContract[CreateClientNoteCommand, ClientNoteList]
    ] = Factory(
        CreateClientNoteUseCase,
        board=client_note_board,
        client_note_repo=repositories.client_note_repo,
        wall_clock=wall_clock,
    )
    update_client_note_use_case: Factory[
        UseCaseContract[UpdateClientNoteCommand, ClientNoteList]
    ] = Factory(
        UpdateClientNoteUseCase,
        board=client_note_board,
        client_note_repo=repositories.client_note_repo,
        wall_clock=wall_clock,
    )
    delete_client_note_use_case: Factory[
        UseCaseContract[DeleteClientNoteCommand, None]
    ] = Factory(
        DeleteClientNoteUseCase,
        board=client_note_board,
        client_note_repo=repositories.client_note_repo,
    )
    get_client_timeline_use_case: Factory[
        UseCaseContract[ClientTimelineQuery, ClientTimelinePage]
    ] = Factory(
        GetClientTimelineUseCase,
        authorize_platform_admin=authorize,
        business_repo=repositories.business_repo,
        audit_log_repo=repositories.audit_log_repo,
        invoice_repo=repositories.invoice_repo,
        billing_credit_repo=repositories.billing_credit_repo,
        product_event_repo=repositories.product_event_repo,
        client_health_change_repo=repositories.client_health_change_repo,
        onboarding_request_repo=repositories.onboarding_request_repo,
        user_repo=repositories.user_repo,
    )

    # --- The daily digest of clients that newly turned critical.
    send_critical_clients_digest_use_case: Factory[
        UseCaseContract[JobTick, JobReport]
    ] = Factory(
        SendCriticalClientsDigestUseCase,
        health_change_repo=repositories.client_health_change_repo,
        client_standing_repo=repositories.client_standing_repo,
        digest_state_repo=repositories.admin_digest_state_repo,
        job_queue=facilitators.job_queue_facilitator,
        alert_settings=config.app_settings.provided.platform_alerts,
        cabinet_base_url=config.app_settings.provided.cabinet_base_url,
        wall_clock=wall_clock,
        unit_of_work=adapters.storage_unit_of_work,
    )
