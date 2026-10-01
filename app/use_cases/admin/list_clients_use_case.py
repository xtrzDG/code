from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.client_health import ClientHealthStatus
from app.schemas.domain.users import UserDocument
from app.schemas.dto.admin import (
    AdminClientList,
    AdminClientsQuery,
    AdminClientSummary,
    ClientSummarySource,
)
from app.schemas.typings.client_health.constrained_integers import ClientCount
from app.schemas.typings.users.prefixed_id import UserId

HEALTH_ORDER: dict[ClientHealthStatus, int] = {
    ClientHealthStatus.CRITICAL: 0,
    ClientHealthStatus.ATTENTION: 1,
    ClientHealthStatus.HEALTHY: 2,
}


class ListClientsUseCase(UseCaseContract[AdminClientsQuery, AdminClientList]):
    """
    Every client business for the platform admin (concept /admin): status,
    plan, published version, last autotest, handoffs, open questions, usage
    and margin. Critical clients come first, then those needing attention;
    names order each group.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[UserId, UserDocument],
        business_repo: BusinessRepoContract,
        summarize_client: UseCaseContract[ClientSummarySource, AdminClientSummary],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[UserId, UserDocument] = (
            authorize_platform_admin
        )
        self._business_repo: BusinessRepoContract = business_repo
        self._summarize_client: UseCaseContract[
            ClientSummarySource,
            AdminClientSummary,
        ] = summarize_client
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: AdminClientsQuery) -> AdminClientList:
        self._authorize_platform_admin.run(input_data.user_id)
        summaries: list[AdminClientSummary] = [
            self._summarize_client.run(ClientSummarySource(business=business))
            for business in self._business_repo.list_all()
        ]
        summaries.sort(
            key=lambda summary: (
                HEALTH_ORDER[summary.health_status],
                str(summary.name).casefold(),
                str(summary.business_id),
            )
        )
        return AdminClientList(
            generated_at=self._wall_clock.now_unix(),
            client_count=ClientCount(len(summaries)),
            clients=summaries,
        )
