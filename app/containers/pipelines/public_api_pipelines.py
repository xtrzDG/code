from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.public_api_orchestrators import (
    PublicApiOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class PublicApiPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of the API keys and the public API (1181)."""

    public_api: PublicApiOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    list_api_keys_pipeline = orchestrator_pipeline(
        public_api.list_api_keys_orchestrator
    )
    create_api_key_pipeline = orchestrator_pipeline(
        public_api.create_api_key_orchestrator
    )
    revoke_api_key_pipeline = orchestrator_pipeline(
        public_api.revoke_api_key_orchestrator
    )
    authenticate_api_key_pipeline = orchestrator_pipeline(
        public_api.authenticate_api_key_orchestrator
    )
    get_public_identity_pipeline = orchestrator_pipeline(
        public_api.get_public_identity_orchestrator
    )
    list_public_bookings_pipeline = orchestrator_pipeline(
        public_api.list_public_bookings_orchestrator
    )
    get_public_booking_pipeline = orchestrator_pipeline(
        public_api.get_public_booking_orchestrator
    )
    list_public_leads_pipeline = orchestrator_pipeline(
        public_api.list_public_leads_orchestrator
    )
    get_public_lead_pipeline = orchestrator_pipeline(
        public_api.get_public_lead_orchestrator
    )
    list_public_contacts_pipeline = orchestrator_pipeline(
        public_api.list_public_contacts_orchestrator
    )
    get_public_contact_pipeline = orchestrator_pipeline(
        public_api.get_public_contact_orchestrator
    )
    list_public_conversations_pipeline = orchestrator_pipeline(
        public_api.list_public_conversations_orchestrator
    )
    get_public_conversation_pipeline = orchestrator_pipeline(
        public_api.get_public_conversation_orchestrator
    )
    subscribe_public_webhook_pipeline = orchestrator_pipeline(
        public_api.subscribe_public_webhook_orchestrator
    )
    unsubscribe_public_webhook_pipeline = orchestrator_pipeline(
        public_api.unsubscribe_public_webhook_orchestrator
    )
    create_public_booking_pipeline = orchestrator_pipeline(
        public_api.create_public_booking_orchestrator
    )
    create_public_lead_pipeline = orchestrator_pipeline(
        public_api.create_public_lead_orchestrator
    )
