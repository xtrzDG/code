from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.booking_link_pipelines import (
    BookingLinkPipelinesContainer,
)
from app.containers.provider_chains import pipeline_operator
from app.containers.utilities import UtilitiesContainer


class BookingLinkOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of a guest's booking page. The request names no business (the
    link does), so the operator runs unscoped and the orchestrator enters
    the business's scope once the link checked out.
    """

    booking_link_pipelines: BookingLinkPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    managed_booking_operator = pipeline_operator(
        booking_link_pipelines.managed_booking_pipeline, storage_scope
    )
    managed_booking_calendar_operator = pipeline_operator(
        booking_link_pipelines.managed_booking_calendar_pipeline, storage_scope
    )
    managed_booking_slots_operator = pipeline_operator(
        booking_link_pipelines.managed_booking_slots_pipeline, storage_scope
    )
    cancel_managed_booking_operator = pipeline_operator(
        booking_link_pipelines.cancel_managed_booking_pipeline, storage_scope
    )
    reschedule_managed_booking_operator = pipeline_operator(
        booking_link_pipelines.reschedule_managed_booking_pipeline, storage_scope
    )
