"""
The admin client list's search: part of a client's name or id.

Names have no index, so a search walks the stored standings in the list's
order, in keyset batches, and one request looks at most at
`SEARCH_SCAN_LIMIT` clients: `matching_count` counts the matches among
them (every match while the platform has fewer clients), and the cursor
goes on after the last match shown, or after the last client looked at
when the walk stopped there ("Load more" searches further).
"""

from dataclasses import dataclass

from app.contracts.repositories.client_standing_repositories import (
    ClientStandingRepoContract,
)
from app.schemas.constants.client_health import AdminClientSort
from app.schemas.domain.client_standings import ClientStandingDocument
from app.schemas.dto.client_standings import ClientStandingFilter
from app.schemas.dto.paging import KeysetPosition, KeysetSlice, PageRequest
from app.schemas.typings.client_health.constrained_integers import ClientCount
from app.schemas.typings.client_health.constrained_strings import ClientSearchText
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.use_cases.admin.client_list_order import matches_search
from app.utilities.paging.cursor_paging import encode_page_cursor
from app.utilities.paging.keyset_paging import read_slice, single_value_position

SEARCH_BATCH: int = 200
SEARCH_SCAN_LIMIT: int = 2_000


@dataclass(frozen=True)
class ClientSearchPage:
    """The clients one search request found, and where to go on."""

    standings: list[ClientStandingDocument]
    next_cursor: PageCursor | None
    matching_count: ClientCount


def position_in(standing: ClientStandingDocument, sort: AdminClientSort) -> int:
    """The client's position in the order `sort`."""

    return int(
        {
            AdminClientSort.HEALTH: standing.health_position,
            AdminClientSort.NAME: standing.name_position,
            AdminClientSort.USAGE: standing.usage_position,
            AdminClientSort.MARGIN: standing.margin_position,
            AdminClientSort.COST: standing.cost_position,
            AdminClientSort.REVENUE: standing.revenue_position,
        }[sort]
    )


def search_standings(
    standing_repo: ClientStandingRepoContract,
    sort: AdminClientSort,
    where: ClientStandingFilter,
    search: ClientSearchText,
    page: PageRequest,
) -> ClientSearchPage:
    """
    Raises:
        ValidationFailedError: the cursor is broken.
    """

    size: int = int(page.size)
    after: KeysetPosition | None = read_slice(page).after
    matches: list[ClientStandingDocument] = []
    scanned: int = 0
    last: ClientStandingDocument | None = None
    is_walked: bool = False
    while scanned < SEARCH_SCAN_LIMIT and not is_walked:
        batch: list[ClientStandingDocument] = standing_repo.page(
            sort, where, KeysetSlice(after=after, limit=KeysetReadLimit(SEARCH_BATCH))
        )
        for standing in batch:
            scanned += 1
            last = standing
            if matches_search(str(standing.name), str(standing.business_id), search):
                matches.append(standing)

        is_walked = len(batch) < SEARCH_BATCH or last is None
        if last is not None:
            after = single_value_position(
                position_in(last, sort), str(last.business_id)
            )

    shown: list[ClientStandingDocument] = matches[:size]
    next_cursor: PageCursor | None = None
    if len(matches) > size:
        next_cursor = cursor_after(shown[-1], sort)
    elif not is_walked and last is not None:
        next_cursor = cursor_after(last, sort)

    return ClientSearchPage(
        standings=shown,
        next_cursor=next_cursor,
        matching_count=ClientCount(len(matches)),
    )


def cursor_after(standing: ClientStandingDocument, sort: AdminClientSort) -> PageCursor:
    return encode_page_cursor(position_in(standing, sort), str(standing.business_id))
