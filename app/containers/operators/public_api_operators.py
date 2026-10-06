from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.public_api_pipelines import PublicApiPipelinesContainer
from app.containers.provider_chains import pipeline_operator
from app.containers.utilities import UtilitiesContainer


class PublicApiOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the API keys and the public API: each in the business's
    scope its input names (the cabinet's path, or the authenticated key's
    business); the authentication itself names none, so its use case
    finds the key across businesses by its hash and then enters its scope.
    """

    public_api_pipelines: PublicApiPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope
    pipelines = public_api_pipelines

    list_api_keys_operator = pipeline_operator(
        pipelines.list_api_keys_pipeline, storage_scope
    )
    create_api_key_operator = pipeline_operator(
        pipelines.create_api_key_pipeline, storage_scope
    )
    revoke_api_key_operator = pipeline_operator(
        pipelines.revoke_api_key_pipeline, storage_scope
    )
    authenticate_api_key_operator = pipeline_operator(
        pipelines.authenticate_api_key_pipeline, storage_scope
    )
    get_public_identity_operator = pipeline_operator(
        pipelines.get_public_identity_pipeline, storage_scope
    )
    list_public_bookings_operator = pipeline_operator(
        pipelines.list_public_bookings_pipeline, storage_scope
    )
    get_public_booking_operator = pipeline_operator(
        pipelines.get_public_booking_pipeline, storage_scope
    )
    list_public_leads_operator = pipeline_operator(
        pipelines.list_public_leads_pipeline, storage_scope
    )
    get_public_lead_operator = pipeline_operator(
        pipelines.get_public_lead_pipeline, storage_scope
    )
    list_public_contacts_operator = pipeline_operator(
        pipelines.list_public_contacts_pipeline, storage_scope
    )
    get_public_contact_operator = pipeline_operator(
        pipelines.get_public_contact_pipeline, storage_scope
    )
    list_public_conversations_operator = pipeline_operator(
        pipelines.list_public_conversations_pipeline, storage_scope
    )
    get_public_conversation_operator = pipeline_operator(
        pipelines.get_public_conversation_pipeline, storage_scope
    )
    subscribe_public_webhook_operator = pipeline_operator(
        pipelines.subscribe_public_webhook_pipeline, storage_scope
    )
    unsubscribe_public_webhook_operator = pipeline_operator(
        pipelines.unsubscribe_public_webhook_pipeline, storage_scope
    )
    create_public_booking_operator = pipeline_operator(
        pipelines.create_public_booking_pipeline, storage_scope
    )
    create_public_lead_operator = pipeline_operator(
        pipelines.create_public_lead_pipeline, storage_scope
    )
