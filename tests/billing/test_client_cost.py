"""A client's cost, revenue and margin for the platform admin."""

from decimal import Decimal

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.billing import InvoiceKind, InvoiceStatus, UsageKind
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.dto.billing_ledger import ClientCostQuery
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.billing.strings import InvoiceDescription
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.billing.client_cost_math import (
    compute_margin_percent,
    compute_period_share,
)
from tests.billing.billing_registries import StaticExchangeRateRegistry
from tests.billing.billing_settings import GEORGIA, ITALY
from tests.billing.billing_testbed import BillingTestbed
from tests.billing.cost_world import PERIOD_DAYS, CostWorld


def test_cost_counts_language_model_spend_once_and_compares_with_revenue() -> None:
    world = CostWorld(
        BillingTestbed(
            exchange_rate_registry=StaticExchangeRateRegistry([("EUR", "USD", 1.1)])
        ),
        ITALY,
    )
    world.record_typical_month()

    report = world.report()

    assert int(report.llm_cost_micro_usd) == 6_800_000
    assert int(report.provider_cost_micro_usd) == 39_280_000
    assert [
        (line.kind, int(line.quantity), int(line.cost_micro_usd))
        for line in (report.usage_cost_lines)
    ] == [
        (UsageKind.VOICE_SECONDS, 18_000, 24_000_000),
        (UsageKind.LLM_INPUT_TOKENS, 50_000, 3_800_000),
        (UsageKind.LLM_OUTPUT_TOKENS, 4_000, 2_000_000),
        (UsageKind.DIALOG, 3, 0),
        (UsageKind.WHATSAPP_REPLY, 400, 8_480_000),
    ]
    assert int(report.revenue.amount_minor) == 17500
    assert report.provider_cost is not None
    assert int(report.provider_cost.amount_minor) == 3571
    assert report.margin is not None
    assert int(report.margin.amount_minor) == 13929
    assert report.margin_percent == pytest.approx(79.59)
    assert report.exchange_rate is not None
    assert report.exchange_rate.base_currency_code == "EUR"
    assert report.planned_monthly_provider_cost is not None
    assert int(report.planned_monthly_provider_cost.amount_minor) == 5490


def test_cost_in_lari_with_a_direct_dollar_rate() -> None:
    world = CostWorld(
        BillingTestbed(
            exchange_rate_registry=StaticExchangeRateRegistry([("USD", "GEL", 2.7)])
        ),
        GEORGIA,
    )
    world.record_typical_month()

    report = world.report()

    assert report.revenue.currency_code == "GEL"
    assert int(report.revenue.amount_minor) == 51700
    assert report.provider_cost is not None
    assert int(report.provider_cost.amount_minor) == 10606
    assert report.margin is not None
    assert int(report.margin.amount_minor) == 41094


def test_without_an_official_dollar_rate_the_margin_stays_unknown() -> None:
    world = CostWorld(BillingTestbed(), GEORGIA)
    world.record_typical_month()

    report = world.report()

    assert int(report.provider_cost_micro_usd) == 39_280_000
    assert report.provider_cost is None
    assert report.margin is None
    assert report.margin_percent is None
    assert report.exchange_rate is None


def test_revenue_is_prorated_and_a_setup_fee_counts_when_invoiced() -> None:
    world = CostWorld(
        BillingTestbed(
            exchange_rate_registry=StaticExchangeRateRegistry([("EUR", "USD", 1.1)])
        ),
        ITALY,
    )
    world.add_invoice(InvoiceKind.SETUP_FEE, 15000, "EUR", world.at(1), world.at(1))
    world.add_invoice(
        InvoiceKind.SERVICE_PERIOD,
        17500,
        "EUR",
        world.period_end,
        world.at(2 * PERIOD_DAYS),
        status=InvoiceStatus.ISSUED,
    )

    first_half = world.report(period_end=world.at(PERIOD_DAYS / 2))
    second_half = world.report(period_start=world.at(PERIOD_DAYS / 2))

    assert int(first_half.revenue.amount_minor) == 8750 + 15000
    assert int(second_half.revenue.amount_minor) == 8750
    assert first_half.margin_percent == 100.0


def test_a_loss_has_a_negative_margin() -> None:
    world = CostWorld(
        BillingTestbed(
            exchange_rate_registry=StaticExchangeRateRegistry([("EUR", "USD", 1.0)])
        ),
        ITALY,
    )
    world.testbed.record_usage(
        world.business.id,
        UsageKind.VOICE_SECONDS,
        120_000,
        350_000_000,
        None,
        world.at(1),
    )

    report = world.report()

    assert report.margin is not None
    assert int(report.margin.amount_minor) == 17500 - 35000
    assert report.margin_percent == pytest.approx(-100.0)


def test_cost_queries_are_validated() -> None:
    world = CostWorld(BillingTestbed(), ITALY)

    with pytest.raises(ValidationFailedError):
        world.report(period_start=world.period_end, period_end=world.period_start)

    with pytest.raises(NotFoundError):
        world.testbed.compute_client_cost.run(
            ClientCostQuery(
                business_id=BusinessId(),
                period_start=world.period_start,
                period_end=world.period_end,
            )
        )


def test_period_share_and_margin_helpers() -> None:
    invoice = InvoiceDocument(
        business_id=BusinessId(),
        description=InvoiceDescription("Call and message handling service"),
        amount_minor=MoneyAmountMinor(100),
        currency_code=CurrencyCode("EUR"),
        period_start=Microseconds(100),
        period_end=Microseconds(200),
    )
    query = ClientCostQuery(
        business_id=invoice.business_id,
        period_start=Microseconds(150),
        period_end=Microseconds(400),
    )
    outside = ClientCostQuery(
        business_id=invoice.business_id,
        period_start=Microseconds(200),
        period_end=Microseconds(300),
    )

    assert compute_period_share(invoice, query) == Decimal("0.5")
    assert compute_period_share(invoice, outside) == 0
    assert compute_margin_percent(0, 10) is None
    assert compute_margin_percent(3, 1) == pytest.approx(66.67)
