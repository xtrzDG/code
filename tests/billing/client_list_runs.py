"""The admin client list as the platform runs it: the standings job, then a read."""

from app.gateways.worker.periodic.refresh_client_standings import (
    REFRESH_CLIENT_STANDINGS_JOB,
)
from app.schemas.dto.admin import AdminClientPage, AdminClientsQuery
from app.schemas.dto.jobs import JobReport, JobTick
from app.use_cases.admin.list_clients_use_case import ListClientsUseCase
from app.use_cases.admin.refresh_client_standings_use_case import (
    RefreshClientStandingsUseCase,
)
from tests.billing.billing_use_cases import BillingUseCases


def refresh_standings(
    testbed: BillingUseCases,
    refresh: RefreshClientStandingsUseCase | None = None,
) -> JobReport:
    """One run of the `refresh_client_standings` job."""

    return (refresh or testbed.refresh_client_standings).run(
        JobTick(job_name=REFRESH_CLIENT_STANDINGS_JOB, scheduled_at=testbed.clock.now())
    )


def list_clients(
    testbed: BillingUseCases,
    query: AdminClientsQuery,
    list_use_case: ListClientsUseCase | None = None,
) -> AdminClientPage:
    """The client list right after a refresh of the standings."""

    refresh_standings(testbed)
    return (list_use_case or testbed.list_clients).run(query)
