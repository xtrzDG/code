from pydantic import ValidationError
from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.client_standing_repositories import (
    ClientStandingRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.client_standings import ClientStandingDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.admin import (
    AdminClientPage,
    AdminClientsQuery,
    AdminClientSummary,
    ClientSummarySource,
)
from app.schemas.dto.client_standings import ClientChoices, ClientStandingFilter
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.client_health.constrained_integers import ClientCount
from app.schemas.typings.client_health.constrained_strings import ClientSearchText
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.use_cases.admin.client_list_search import (
    ClientSearchPage,
    position_in,
    search_standings,
)
from app.utilities.paging.keyset_paging import finish_page, read_slice


class ListClientsUseCase(UseCaseContract[AdminClientsQuery, AdminClientPage]):
    """
    Clients of the platform for the platform admin (concept /admin): status,
    plan, published version, last autotest, handoffs, open questions, usage
    and margin.

    The list reads the client standings the `refresh_client_standings`
    job stores every few minutes: one keyset page in the chosen order
    (critical clients first by default, see AdminClientSort), filtered by
    business status, health, country and niche in the database, with
    database counts for the matching clients, the summary tiles and the
    filter choices; a search walks the standings (`client_list_search`).
    `generated_at` is when the oldest summary on the page was taken; a
    client that signed up since the last refresh appears after the next.
    A stored summary this release cannot read is computed again.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        client_standing_repo: ClientStandingRepoContract,
        business_repo: BusinessRepoContract,
        summarize_client: UseCaseContract[ClientSummarySource, AdminClientSummary],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._client_standing_repo: ClientStandingRepoContract = client_standing_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._summarize_client: UseCaseContract[
            ClientSummarySource,
            AdminClientSummary,
        ] = summarize_client
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: AdminClientsQuery) -> AdminClientPage:
        self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.VIEW_CLIENTS,
            )
        )
        where = ClientStandingFilter(
            business_status=input_data.status,
            health_status=input_data.health,
            country_code=input_data.country_code,
            niche_key=input_data.niche_key,
        )
        standings, next_cursor, matching_count = self._read_page(input_data, where)
        choices: ClientChoices = self._client_standing_repo.list_choices()
        return AdminClientPage(
            generated_at=min(
                (standing.updated_at for standing in standings),
                default=self._wall_clock.now_unix(),
            ),
            items=[
                summary
                for summary in (self._summary_of(standing) for standing in standings)
                if summary is not None
            ],
            next_cursor=next_cursor,
            matching_count=matching_count,
            totals=self._client_standing_repo.tally(),
            countries=choices.countries,
            niches=choices.niches,
        )

    def _read_page(
        self,
        input_data: AdminClientsQuery,
        where: ClientStandingFilter,
    ) -> tuple[list[ClientStandingDocument], PageCursor | None, ClientCount]:
        """
        Raises:
            ValidationFailedError: the cursor is broken.
        """

        search: ClientSearchText | None = input_data.search
        if search is not None and str(search).strip() != "":
            exact: ClientStandingDocument | None = self._find_by_id(search, where)
            if exact is not None:
                return [exact], None, ClientCount(1)

            found: ClientSearchPage = search_standings(
                self._client_standing_repo,
                input_data.sort,
                where,
                search,
                input_data.page,
            )
            return found.standings, found.next_cursor, found.matching_count

        standings, next_cursor = finish_page(
            self._client_standing_repo.page(
                input_data.sort, where, read_slice(input_data.page)
            ),
            input_data.page,
            sort_key=lambda standing: position_in(standing, input_data.sort),
            item_id=lambda standing: str(standing.business_id),
        )
        return standings, next_cursor, self._client_standing_repo.count(where)

    def _find_by_id(
        self, search: ClientSearchText, where: ClientStandingFilter
    ) -> ClientStandingDocument | None:
        """The client the search names by its full id, when it passes the filter."""

        try:
            business_id = BusinessId(str(search).strip())
        except ValueError, TypeError:
            return None

        standing: ClientStandingDocument | None = self._client_standing_repo.get_many(
            [business_id]
        ).get(business_id)
        if standing is None or not passes(standing, where):
            return None

        return standing

    def _summary_of(
        self, standing: ClientStandingDocument
    ) -> AdminClientSummary | None:
        try:
            return AdminClientSummary.model_validate_json(str(standing.summary))
        except ValidationError:
            # Stored by another release (a deploy): computed again.
            business: BusinessDocument | None = self._business_repo.get(
                standing.business_id
            )
            if business is None:
                return None

            return self._summarize_client.run(ClientSummarySource(business=business))


def passes(standing: ClientStandingDocument, where: ClientStandingFilter) -> bool:
    return all(
        wanted is None or wanted == actual
        for wanted, actual in (
            (where.business_status, standing.business_status),
            (where.health_status, standing.health_status),
            (where.country_code, standing.country_code),
            (where.niche_key, standing.niche_key),
        )
    )
