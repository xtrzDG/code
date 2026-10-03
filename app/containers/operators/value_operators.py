from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.value_pipelines import ValuePipelinesContainer
from app.containers.provider_chains import (
    pipeline_operator,
    platform_pipeline_operator,
)
from app.containers.utilities import UtilitiesContainer


class ValueOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the value context: the cabinet's endpoints run in the
    storage scope of their business; the hourly report job walks every
    business (platform-wide).
    """

    value_pipelines: ValuePipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    get_business_value_operator = pipeline_operator(
        value_pipelines.get_business_value_pipeline, storage_scope
    )
    get_value_settings_operator = pipeline_operator(
        value_pipelines.get_value_settings_pipeline, storage_scope
    )
    update_value_settings_operator = pipeline_operator(
        value_pipelines.update_value_settings_pipeline, storage_scope
    )
    get_digest_preferences_operator = pipeline_operator(
        value_pipelines.get_digest_preferences_pipeline, storage_scope
    )
    update_digest_preferences_operator = pipeline_operator(
        value_pipelines.update_digest_preferences_pipeline, storage_scope
    )
    list_value_reports_operator = pipeline_operator(
        value_pipelines.list_value_reports_pipeline, storage_scope
    )
    get_value_report_operator = pipeline_operator(
        value_pipelines.get_value_report_pipeline, storage_scope
    )
    get_today_queue_operator = pipeline_operator(
        value_pipelines.get_today_queue_pipeline, storage_scope
    )
    send_value_reports_operator = platform_pipeline_operator(
        value_pipelines.send_value_reports_pipeline, storage_scope
    )
