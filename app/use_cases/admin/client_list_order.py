"""
The orders of the platform admin's client list, as sort keys of a client's
summary (`AdminClientSort`). The `refresh_client_standings` job ranks every
client by each of them; the list then pages by the stored position.
"""

from collections.abc import Callable

from app.schemas.constants.client_health import AdminClientSort, ClientHealthStatus
from app.schemas.dto.admin import AdminClientSummary
from app.schemas.dto.billing import Money
from app.schemas.typings.billing.constrained_floats import GrossMarginPercent
from app.schemas.typings.client_health.constrained_strings import ClientSearchText

HEALTH_ORDER: dict[ClientHealthStatus, int] = {
    ClientHealthStatus.CRITICAL: 0,
    ClientHealthStatus.ATTENTION: 1,
    ClientHealthStatus.HEALTHY: 2,
}

# Sort keys put unknown values last: (1, ...) after (0, value).
type SortKey = tuple[object, ...]


def find_usage_percent(summary: AdminClientSummary) -> float | None:
    """The fuller of the two packages (voice minutes, dialogs), or None."""

    percents: list[float] = [
        int(used) / int(included) * 100
        for used, included in (
            (summary.used_voice_minutes, summary.included_voice_minutes),
            (summary.used_dialogs, summary.included_dialogs),
        )
        if int(included) > 0
    ]
    return max(percents, default=None)


def is_losing_money(summary: AdminClientSummary) -> bool:
    """The client's margin in the current window is below zero."""

    return summary.cost.margin is not None and int(summary.cost.margin.amount_minor) < 0


def matches_search(
    summary_name: str, business_id: str, search: ClientSearchText | None
) -> bool:
    """Part of the name or of the id, without case."""

    if search is None:
        return True

    needle: str = str(search).strip().casefold()
    return needle in summary_name.casefold() or needle in business_id.casefold()


def health_key(summary: AdminClientSummary) -> SortKey:
    return (
        HEALTH_ORDER[summary.health_status],
        -len(summary.health_issues),
        *name_key(summary),
    )


def name_key(summary: AdminClientSummary) -> SortKey:
    return (str(summary.name).casefold(), str(summary.business_id))


def known_first(value: float | None) -> SortKey:
    """Unknown values sort after every known one."""

    return (1, 0.0) if value is None else (0, value)


def usage_key(summary: AdminClientSummary) -> SortKey:
    percent: float | None = find_usage_percent(summary)
    return (*known_first(None if percent is None else -percent), *health_key(summary))


def margin_key(summary: AdminClientSummary) -> SortKey:
    margin_percent: GrossMarginPercent | None = summary.cost.margin_percent
    return (
        *known_first(None if margin_percent is None else float(margin_percent)),
        *health_key(summary),
    )


def cost_key(summary: AdminClientSummary) -> SortKey:
    return (-int(summary.cost.provider_cost_micro_usd), *health_key(summary))


def revenue_key(summary: AdminClientSummary) -> SortKey:
    revenue: Money = summary.cost.revenue
    return (
        str(revenue.currency_code),
        -int(revenue.amount_minor),
        *health_key(summary),
    )


SORT_KEYS: dict[AdminClientSort, Callable[[AdminClientSummary], SortKey]] = {
    AdminClientSort.HEALTH: health_key,
    AdminClientSort.NAME: name_key,
    AdminClientSort.USAGE: usage_key,
    AdminClientSort.MARGIN: margin_key,
    AdminClientSort.COST: cost_key,
    AdminClientSort.REVENUE: revenue_key,
}
