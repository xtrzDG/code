from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.call_use_cases import CallUseCasesContainer
from app.contracts.orchestrator_contract import OrchestratorContract
from app.orchestrators.voice.missed_call_orchestrator import MissedCallOrchestrator
from app.orchestrators.voice.pbx_call_webhook_orchestrator import (
    PbxCallWebhookOrchestrator,
)
from app.schemas.dto.calls.missed_calls import (
    MissedCallReport,
    PbxCallWebhookOutcome,
    PbxCallWebhookRequest,
    RegisteredMissedCall,
)


class CallOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators of what follows a phone call: a caller who did not get
    through (the telephony line's webhook, a failed start), the text-back
    job and Settings → Calls.
    """

    call_use_cases: CallUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    missed_call_orchestrator: Factory[
        OrchestratorContract[MissedCallReport, RegisteredMissedCall | None]
    ] = Factory(
        MissedCallOrchestrator,
        register_missed_call=call_use_cases.register_missed_call_use_case,
        notify_missed_call=call_use_cases.notify_missed_call_use_case,
    )
    pbx_call_webhook_orchestrator: Factory[
        OrchestratorContract[PbxCallWebhookRequest, PbxCallWebhookOutcome]
    ] = Factory(
        PbxCallWebhookOrchestrator,
        read_pbx_missed_call=call_use_cases.read_pbx_missed_call_use_case,
        handle_missed_call=missed_call_orchestrator,
    )
    send_text_back_orchestrator = use_case_orchestrator(
        call_use_cases.send_text_back_use_case
    )
    get_call_settings_orchestrator = use_case_orchestrator(
        call_use_cases.get_call_settings_use_case
    )
    update_call_settings_orchestrator = use_case_orchestrator(
        call_use_cases.update_call_settings_use_case
    )
    list_text_backs_orchestrator = use_case_orchestrator(
        call_use_cases.list_text_backs_use_case
    )
