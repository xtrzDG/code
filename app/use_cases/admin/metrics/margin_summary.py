"""Gross margin over many clients: the admin's client cost reports, in euros."""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.analytics.revenue_views import MarginView
from app.schemas.dto.billing_ledger import ClientCostQuery, ClientCostReport
from app.schemas.typings.analytics.constrained_integers import AccountCount
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.analytics.euro_conversion import (
    euro_converter,
    provider_cost_in_euros,
)
from app.utilities.analytics.mrr_math import euros
from app.utilities.billing.client_cost_math import compute_margin_percent


def summarize_margin(
    business_ids: Sequence[BusinessId],
    period_start: Microseconds,
    period_end: Microseconds,
    compute_client_cost: UseCaseContract[ClientCostQuery, ClientCostReport],
    registry: ExchangeRateRegistryContract,
) -> MarginView:
    """
    Revenue (paid invoices, prorated) and provider cost of each business
    for the period, both in euros, summed over the clients that had either;
    a client whose revenue or cost has no official rate to euros is left out
    and counted.
    """

    to_eur = euro_converter(registry)
    revenue = cost = accounts = without_rate = 0
    for business_id in business_ids:
        report: ClientCostReport = compute_client_cost.run(
            ClientCostQuery(
                business_id=business_id,
                period_start=period_start,
                period_end=period_end,
            )
        )
        revenue_minor: int = int(report.revenue.amount_minor)
        cost_micro_usd: int = int(report.provider_cost_micro_usd)
        if revenue_minor == 0 and cost_micro_usd == 0:
            continue

        revenue_eur = (
            0
            if revenue_minor == 0
            else to_eur(revenue_minor, report.revenue.currency_code)
        )
        cost_eur = provider_cost_in_euros(cost_micro_usd, registry)
        if revenue_eur is None or cost_eur is None:
            without_rate += 1
            continue

        revenue += revenue_eur
        cost += cost_eur
        accounts += 1

    return MarginView(
        revenue=euros(revenue),
        provider_cost=euros(cost),
        gross_margin_percent=compute_margin_percent(revenue, cost),
        accounts=AccountCount(accounts),
        accounts_without_rate=AccountCount(without_rate),
    )
