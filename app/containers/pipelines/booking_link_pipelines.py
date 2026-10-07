from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.booking_link_orchestrators import (
    BookingLinkOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class BookingLinkPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of a guest's booking page (one orchestrator each)."""

    booking_link_orchestrators: BookingLinkOrchestratorsContainer = (
        DependenciesContainer()  # type: ignore[assignment]
    )

    managed_booking_pipeline = orchestrator_pipeline(
        booking_link_orchestrators.managed_booking_orchestrator
    )
    managed_booking_calendar_pipeline = orchestrator_pipeline(
        booking_link_orchestrators.managed_booking_calendar_orchestrator
    )
    managed_booking_slots_pipeline = orchestrator_pipeline(
        booking_link_orchestrators.managed_booking_slots_orchestrator
    )
    cancel_managed_booking_pipeline = orchestrator_pipeline(
        booking_link_orchestrators.cancel_managed_booking_orchestrator
    )
    reschedule_managed_booking_pipeline = orchestrator_pipeline(
        booking_link_orchestrators.reschedule_managed_booking_orchestrator
    )
