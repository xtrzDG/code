from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.call_orchestrators import (
    CallOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class CallPipelinesContainer(containers.DeclarativeContainer):
    """
    Pipelines of the telephony line's webhook, the call fallback of rented
    numbers, text-backs, Settings → Calls
    and the phone line's rented number (1213).
    """

    calls: CallOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    pbx_call_webhook_pipeline = orchestrator_pipeline(
        calls.pbx_call_webhook_orchestrator
    )
    call_fallback_pipeline = orchestrator_pipeline(calls.call_fallback_orchestrator)
    fallback_dial_pipeline = orchestrator_pipeline(calls.fallback_dial_orchestrator)
    send_text_back_pipeline = orchestrator_pipeline(calls.send_text_back_orchestrator)
    get_call_settings_pipeline = orchestrator_pipeline(
        calls.get_call_settings_orchestrator
    )
    update_call_settings_pipeline = orchestrator_pipeline(
        calls.update_call_settings_orchestrator
    )
    list_text_backs_pipeline = orchestrator_pipeline(calls.list_text_backs_orchestrator)
    get_phone_line_pipeline = orchestrator_pipeline(calls.get_phone_line_orchestrator)
    search_phone_numbers_pipeline = orchestrator_pipeline(
        calls.search_phone_numbers_orchestrator
    )
    rent_phone_number_pipeline = orchestrator_pipeline(
        calls.rent_phone_number_orchestrator
    )
    request_phone_number_pipeline = orchestrator_pipeline(
        calls.request_phone_number_orchestrator
    )
    cancel_phone_number_request_pipeline = orchestrator_pipeline(
        calls.cancel_phone_number_request_orchestrator
    )
    maintain_phone_numbers_pipeline = orchestrator_pipeline(
        calls.maintain_phone_numbers_orchestrator
    )
    bill_phone_number_rentals_pipeline = orchestrator_pipeline(
        calls.bill_phone_number_rentals_orchestrator
    )
