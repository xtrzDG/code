from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, List, Singleton

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.facilitators.integrations.emit_business_event_facilitator import (
    EmitBusinessEventFacilitator,
)
from app.facilitators.integrations.public_record_reader_facilitator import (
    PublicRecordReaderFacilitator,
)
from app.facilitators.jobs.job_queue_facilitator import JobQueueFacilitator


class IntegrationFacilitatorsContainer(containers.DeclarativeContainer):
    """
    The public API and outbound webhooks: records in their public shape,
    and the observer of the event publisher that turns announced changes
    into webhook deliveries (`business_event_observers`, handed to the
    publisher by `LiveFacilitatorsContainer`). A child of
    FacilitatorsContainer (`facilitators.public_record_reader`).
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    public_record_reader: Singleton[PublicRecordReaderFacilitator] = Singleton(
        PublicRecordReaderFacilitator,
        booking_repo=repositories.booking_repo,
        lead_repo=repositories.lead_repo,
        handoff_repo=repositories.handoff_repo,
        contact_repo=repositories.contact_repo,
        conversation_repo=repositories.conversation_repo,
        message_repo=repositories.message_repo,
        call_repo=repositories.call_repo,
        resource_repo=repositories.resource_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
    )
    # The webhooks' own handle on the durable job queue (the queue itself
    # is the shared `queued_jobs` collection).
    webhook_job_queue: Singleton[JobQueueFacilitator] = Singleton(
        JobQueueFacilitator,
        job_repo=repositories.queued_job_repo,
        job_wakeup=adapters.job_wakeup,
        unit_of_work=adapters.storage_unit_of_work,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    emit_business_event: Singleton[EmitBusinessEventFacilitator] = Singleton(
        EmitBusinessEventFacilitator,
        business_repo=repositories.business_repo,
        endpoint_repo=repositories.webhook_endpoint_repo,
        delivery_repo=repositories.webhook_delivery_repo,
        record_reader=public_record_reader,
        job_queue=webhook_job_queue,
        unit_of_work=adapters.storage_unit_of_work,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    business_event_observers: List[EmitBusinessEventFacilitator] = List(
        emit_business_event
    )
