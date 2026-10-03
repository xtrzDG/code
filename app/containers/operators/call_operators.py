from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.call_pipelines import CallPipelinesContainer
from app.containers.provider_chains import (
    pipeline_operator,
    platform_pipeline_operator,
)
from app.containers.utilities import UtilitiesContainer


class CallOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of what follows a phone call: the telephony line's webhook
    (platform-wide: its business is known only from the called number),
    the text-back job (in its business's scope) and Settings → Calls.
    """

    call_pipelines: CallPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    pbx_call_webhook_operator = platform_pipeline_operator(
        call_pipelines.pbx_call_webhook_pipeline, storage_scope
    )
    send_text_back_operator = pipeline_operator(
        call_pipelines.send_text_back_pipeline, storage_scope
    )
    get_call_settings_operator = pipeline_operator(
        call_pipelines.get_call_settings_pipeline, storage_scope
    )
    update_call_settings_operator = pipeline_operator(
        call_pipelines.update_call_settings_pipeline, storage_scope
    )
    list_text_backs_operator = pipeline_operator(
        call_pipelines.list_text_backs_pipeline, storage_scope
    )
