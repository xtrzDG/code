from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Dependency, Factory

from app.containers.phone_numbers.phone_number_root import PhoneNumberRoot
from app.containers.phone_numbers.phone_number_use_case_factories import (
    PhoneNumberUseCaseFactories as PhoneNumbers,
)
from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.call_use_cases import CallUseCasesContainer
from app.contracts.orchestrator_contract import OrchestratorContract
from app.orchestrators.voice.call_fallback_orchestrator import (
    CallFallbackOrchestrator,
)
from app.orchestrators.voice.fallback_dial_orchestrator import (
    FallbackDialOrchestrator,
)
from app.orchestrators.voice.missed_call_orchestrator import MissedCallOrchestrator
from app.orchestrators.voice.pbx_call_webhook_orchestrator import (
    PbxCallWebhookOrchestrator,
)
from app.schemas.dto.calls.call_fallback import (
    CallFallbackReply,
    CallFallbackWebhookRequest,
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
    through (the telephony line's webhook, a failed start), the call
    fallback of rented numbers (put through to staff), the text-back
    job and Settings → Calls; and the phone line's number the platform
    rents (1213): the cabinet's phone line and the numbers' two jobs.
    """

    call_use_cases: CallUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    # The phone numbers context's typed root (app/containers/phone_numbers/).
    phone_number_root: Dependency[PhoneNumberRoot] = Dependency(
        instance_of=PhoneNumberRoot
    )
    phone_numbers = phone_number_root.provided.use_cases

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
    call_fallback_orchestrator: Factory[
        OrchestratorContract[CallFallbackWebhookRequest, CallFallbackReply]
    ] = Factory(
        CallFallbackOrchestrator,
        route_call_fallback=call_use_cases.route_call_fallback_use_case,
        notify_call_fallback=call_use_cases.notify_call_fallback_use_case,
        handle_missed_call=missed_call_orchestrator,
    )
    fallback_dial_orchestrator: Factory[
        OrchestratorContract[CallFallbackWebhookRequest, CallFallbackReply]
    ] = Factory(
        FallbackDialOrchestrator,
        read_fallback_dial=call_use_cases.read_fallback_dial_use_case,
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

    # --- The phone line's rented number (1213).
    get_phone_line_orchestrator = use_case_orchestrator(
        Factory(PhoneNumbers.get_phone_line, phone_numbers)
    )
    search_phone_numbers_orchestrator = use_case_orchestrator(
        Factory(PhoneNumbers.search_phone_numbers, phone_numbers)
    )
    rent_phone_number_orchestrator = use_case_orchestrator(
        Factory(PhoneNumbers.rent_phone_number, phone_numbers)
    )
    request_phone_number_orchestrator = use_case_orchestrator(
        Factory(PhoneNumbers.request_phone_number, phone_numbers)
    )
    cancel_phone_number_request_orchestrator = use_case_orchestrator(
        Factory(PhoneNumbers.cancel_phone_number_request, phone_numbers)
    )
    maintain_phone_numbers_orchestrator = use_case_orchestrator(
        Factory(PhoneNumbers.maintain_phone_numbers, phone_numbers)
    )
    bill_phone_number_rentals_orchestrator = use_case_orchestrator(
        Factory(PhoneNumbers.bill_phone_number_rentals, phone_numbers)
    )
