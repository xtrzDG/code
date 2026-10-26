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
    the call fallback of rented numbers (in the scope of the business its
    signed address names),
    the text-back job (in its business's scope) and Settings → Calls; the
    phone line's rented number (1213) in its business's scope, and the
    numbers' two jobs platform-wide (they walk every business's numbers).
    """

    call_pipelines: CallPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    pbx_call_webhook_operator = platform_pipeline_operator(
        call_pipelines.pbx_call_webhook_pipeline, storage_scope
    )
    call_fallback_operator = pipeline_operator(
        call_pipelines.call_fallback_pipeline, storage_scope
    )
    fallback_dial_operator = pipeline_operator(
        call_pipelines.fallback_dial_pipeline, storage_scope
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
    get_phone_line_operator = pipeline_operator(
        call_pipelines.get_phone_line_pipeline, storage_scope
    )
    search_phone_numbers_operator = pipeline_operator(
        call_pipelines.search_phone_numbers_pipeline, storage_scope
    )
    rent_phone_number_operator = pipeline_operator(
        call_pipelines.rent_phone_number_pipeline, storage_scope
    )
    request_phone_number_operator = pipeline_operator(
        call_pipelines.request_phone_number_pipeline, storage_scope
    )
    cancel_phone_number_request_operator = pipeline_operator(
        call_pipelines.cancel_phone_number_request_pipeline, storage_scope
    )
    maintain_phone_numbers_operator = platform_pipeline_operator(
        call_pipelines.maintain_phone_numbers_pipeline, storage_scope
    )
    bill_phone_number_rentals_operator = platform_pipeline_operator(
        call_pipelines.bill_phone_number_rentals_pipeline, storage_scope
    )
