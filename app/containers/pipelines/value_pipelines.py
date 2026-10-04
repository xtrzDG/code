from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.value_orchestrators import (
    ValueOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class ValuePipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of the value context (one orchestrator each)."""

    value: ValueOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    get_business_value_pipeline = orchestrator_pipeline(
        value.get_business_value_orchestrator
    )
    get_value_settings_pipeline = orchestrator_pipeline(
        value.get_value_settings_orchestrator
    )
    update_value_settings_pipeline = orchestrator_pipeline(
        value.update_value_settings_orchestrator
    )
    get_digest_preferences_pipeline = orchestrator_pipeline(
        value.get_digest_preferences_orchestrator
    )
    update_digest_preferences_pipeline = orchestrator_pipeline(
        value.update_digest_preferences_orchestrator
    )
    list_value_reports_pipeline = orchestrator_pipeline(
        value.list_value_reports_orchestrator
    )
    get_value_report_pipeline = orchestrator_pipeline(
        value.get_value_report_orchestrator
    )
    get_today_queue_pipeline = orchestrator_pipeline(value.get_today_queue_orchestrator)
    send_value_reports_pipeline = orchestrator_pipeline(
        value.send_value_reports_orchestrator
    )
    get_customer_sources_pipeline = orchestrator_pipeline(
        value.get_customer_sources_orchestrator
    )
    get_conversation_topics_pipeline = orchestrator_pipeline(
        value.get_conversation_topics_orchestrator
    )
    group_conversation_topics_pipeline = orchestrator_pipeline(
        value.group_conversation_topics_orchestrator
    )
