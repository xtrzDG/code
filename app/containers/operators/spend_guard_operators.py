from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.spend_guard_pipelines import (
    SpendGuardPipelinesContainer,
)
from app.containers.provider_chains import (
    pipeline_operator,
    platform_pipeline_operator,
)
from app.containers.utilities import UtilitiesContainer


class SpendGuardOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the spend guard's endpoints. The admin's spend tile sums
    every business's usage, so it runs platform-wide; the origin check and
    the lists of one business run in its scope, and the generic API limits
    name no business (their counters are a platform table whose adapter
    escalates by itself).
    """

    spend_guard_pipelines: SpendGuardPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    admit_api_request_operator = pipeline_operator(
        spend_guard_pipelines.admit_api_request_pipeline, storage_scope
    )
    check_widget_origin_operator = pipeline_operator(
        spend_guard_pipelines.check_widget_origin_pipeline, storage_scope
    )
    get_widget_allowed_origins_operator = pipeline_operator(
        spend_guard_pipelines.get_widget_allowed_origins_pipeline, storage_scope
    )
    save_widget_allowed_origins_operator = pipeline_operator(
        spend_guard_pipelines.save_widget_allowed_origins_pipeline, storage_scope
    )
    get_platform_spend_operator = platform_pipeline_operator(
        spend_guard_pipelines.get_platform_spend_pipeline, storage_scope
    )
    set_business_spend_limits_operator = pipeline_operator(
        spend_guard_pipelines.set_business_spend_limits_pipeline, storage_scope
    )
