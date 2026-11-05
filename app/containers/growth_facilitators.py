from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Dependency, Singleton

from app.containers.repositories import RepositoriesContainer
from app.containers.utilities import UtilitiesContainer
from app.facilitators.deposits.deposit_aware_growth_facilitator import (
    DepositAwareGrowthFacilitator,
)
from app.facilitators.deposits.deposit_settlement_facilitator import (
    DepositSettlementFacilitator,
)
from app.facilitators.growth.growth_bookings_facilitator import (
    GrowthBookingsFacilitator,
)
from app.facilitators.jobs.job_queue_facilitator import JobQueueFacilitator
from app.facilitators.notifications.staff_alert_facilitator import (
    StaffAlertFacilitator,
)


class GrowthFacilitatorsContainer(containers.DeclarativeContainer):
    """
    The revenue features' side of every booking change (1151): the places
    held for waiting customers, the freed places queued for an offer, the
    revenue line of a new booking; and the deposit of a booking that ended
    (1190). A child of FacilitatorsContainer, which names them flat
    (`facilitators.growth_bookings`, `facilitators.deposit_settlement`).
    """

    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    job_queue: Dependency[JobQueueFacilitator] = Dependency(
        instance_of=JobQueueFacilitator
    )
    staff_alerts: Dependency[StaffAlertFacilitator] = Dependency(
        instance_of=StaffAlertFacilitator
    )

    waitlist_bookings: Singleton[GrowthBookingsFacilitator] = Singleton(
        GrowthBookingsFacilitator,
        waitlist_entry_repo=repositories.waitlist_entry_repo,
        waitlist_settings_repo=repositories.waitlist_settings_repo,
        campaign_message_repo=repositories.campaign_message_repo,
        job_queue=job_queue,
    )
    deposit_settlement: Singleton[DepositSettlementFacilitator] = Singleton(
        DepositSettlementFacilitator,
        deposit_request_repo=repositories.deposit_request_repo,
        deposit_settings_repo=repositories.deposit_settings_repo,
        booking_repo=repositories.booking_repo,
        business_repo=repositories.business_repo,
        staff_alerts=staff_alerts,
        localized_text_resolver=utilities.localized_text_resolver,
    )
    growth_bookings: Singleton[DepositAwareGrowthFacilitator] = Singleton(
        DepositAwareGrowthFacilitator,
        inner=waitlist_bookings,
        deposits=deposit_settlement,
    )
