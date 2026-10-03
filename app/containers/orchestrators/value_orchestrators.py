from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.value_use_cases import ValueUseCasesContainer


class ValueOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators of the value context: the value of a period, the average
    check, digest choices, stored reports, today's queue and the report job.
    """

    value_use_cases: ValueUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    get_business_value_orchestrator = use_case_orchestrator(
        value_use_cases.get_business_value_use_case
    )
    get_value_settings_orchestrator = use_case_orchestrator(
        value_use_cases.get_value_settings_use_case
    )
    update_value_settings_orchestrator = use_case_orchestrator(
        value_use_cases.update_value_settings_use_case
    )
    get_digest_preferences_orchestrator = use_case_orchestrator(
        value_use_cases.get_digest_preferences_use_case
    )
    update_digest_preferences_orchestrator = use_case_orchestrator(
        value_use_cases.update_digest_preferences_use_case
    )
    list_value_reports_orchestrator = use_case_orchestrator(
        value_use_cases.list_value_reports_use_case
    )
    get_value_report_orchestrator = use_case_orchestrator(
        value_use_cases.get_value_report_use_case
    )
    get_today_queue_orchestrator = use_case_orchestrator(
        value_use_cases.get_today_queue_use_case
    )
    send_value_reports_orchestrator = use_case_orchestrator(
        value_use_cases.send_value_reports_use_case
    )
