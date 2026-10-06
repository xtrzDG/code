from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.booking_use_cases import BookingUseCasesContainer
from app.containers.use_cases.follow_up_use_cases import FollowUpUseCasesContainer
from app.containers.use_cases.public_api_use_cases import PublicApiUseCasesContainer
from app.orchestrators.integrations.create_public_records_orchestrators import (
    CreatePublicBookingOrchestrator,
    CreatePublicLeadOrchestrator,
)


class PublicApiOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators of the API keys and the public API (1181): one use case
    each, but the creating operations, which run the cabinet's booking and
    lead use cases between the API's own steps.
    """

    public_api_use_cases: PublicApiUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    booking_use_cases: BookingUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    follow_up_use_cases: FollowUpUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    cases = public_api_use_cases

    list_api_keys_orchestrator = use_case_orchestrator(cases.list_api_keys_use_case)
    create_api_key_orchestrator = use_case_orchestrator(cases.create_api_key_use_case)
    revoke_api_key_orchestrator = use_case_orchestrator(cases.revoke_api_key_use_case)
    authenticate_api_key_orchestrator = use_case_orchestrator(
        cases.authenticate_api_key_use_case
    )
    get_public_identity_orchestrator = use_case_orchestrator(
        cases.get_public_identity_use_case
    )
    list_public_bookings_orchestrator = use_case_orchestrator(
        cases.list_public_bookings_use_case
    )
    get_public_booking_orchestrator = use_case_orchestrator(
        cases.get_public_booking_use_case
    )
    list_public_leads_orchestrator = use_case_orchestrator(
        cases.list_public_leads_use_case
    )
    get_public_lead_orchestrator = use_case_orchestrator(cases.get_public_lead_use_case)
    list_public_contacts_orchestrator = use_case_orchestrator(
        cases.list_public_contacts_use_case
    )
    get_public_contact_orchestrator = use_case_orchestrator(
        cases.get_public_contact_use_case
    )
    list_public_conversations_orchestrator = use_case_orchestrator(
        cases.list_public_conversations_use_case
    )
    get_public_conversation_orchestrator = use_case_orchestrator(
        cases.get_public_conversation_use_case
    )
    subscribe_public_webhook_orchestrator = use_case_orchestrator(
        cases.subscribe_public_webhook_use_case
    )
    unsubscribe_public_webhook_orchestrator = use_case_orchestrator(
        cases.unsubscribe_public_webhook_use_case
    )
    create_public_booking_orchestrator: Factory[CreatePublicBookingOrchestrator] = (
        Factory(
            CreatePublicBookingOrchestrator,
            start_booking=cases.start_public_booking_use_case,
            create_booking=booking_use_cases.create_manual_booking_use_case,
            describe_booking=cases.describe_public_booking_use_case,
        )
    )
    create_public_lead_orchestrator: Factory[CreatePublicLeadOrchestrator] = Factory(
        CreatePublicLeadOrchestrator,
        start_lead=cases.start_public_lead_use_case,
        create_lead=follow_up_use_cases.create_lead_use_case,
        describe_lead=cases.describe_public_lead_use_case,
    )
