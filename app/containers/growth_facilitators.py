from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Dependency, Singleton

from app.containers.repositories import RepositoriesContainer
from app.facilitators.growth.growth_bookings_facilitator import (
    GrowthBookingsFacilitator,
)
from app.facilitators.jobs.job_queue_facilitator import JobQueueFacilitator


class GrowthFacilitatorsContainer(containers.DeclarativeContainer):
    """
    The revenue features' side of every booking change (1151): the places
    held for waiting customers, the freed places queued for an offer, the
    revenue line of a new booking. A child of FacilitatorsContainer, which
    names it flat (`facilitators.growth_bookings`).
    """

    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    job_queue: Dependency[JobQueueFacilitator] = Dependency(
        instance_of=JobQueueFacilitator
    )

    growth_bookings: Singleton[GrowthBookingsFacilitator] = Singleton(
        GrowthBookingsFacilitator,
        waitlist_entry_repo=repositories.waitlist_entry_repo,
        waitlist_settings_repo=repositories.waitlist_settings_repo,
        campaign_message_repo=repositories.campaign_message_repo,
        job_queue=job_queue,
    )
