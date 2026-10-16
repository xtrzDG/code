from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.call_orchestrators import (
    CallOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class CallPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of the telephony line's webhook, text-backs and Settings → Calls."""

    calls: CallOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    pbx_call_webhook_pipeline = orchestrator_pipeline(
        calls.pbx_call_webhook_orchestrator
    )
    send_text_back_pipeline = orchestrator_pipeline(calls.send_text_back_orchestrator)
    get_call_settings_pipeline = orchestrator_pipeline(
        calls.get_call_settings_orchestrator
    )
    update_call_settings_pipeline = orchestrator_pipeline(
        calls.update_call_settings_orchestrator
    )
    list_text_backs_pipeline = orchestrator_pipeline(calls.list_text_backs_orchestrator)
