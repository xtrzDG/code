from decimal import Decimal

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.billing import (
    InvoiceKind,
    InvoiceStatus,
    UsageKind,
)
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.billing_ledger import ClientCostQuery, ClientCostReport
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.billing.constrained_integers import (
    CostMicroUsd,
    MoneyAmountMinor,
)
from app.schemas.typings.billing.strings import InvoiceDescription
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.billing.client_cost_math import (
    compute_margin_percent,
    compute_period_share,
)
from tests.billing.billing_registries import StaticExchangeRateRegistry
from tests.billing.billing_settings import (
    GEORGIA,
    ITALY,
    MICROSECONDS_PER_DAY,
    CountryPreset,
)
from tests.billing.billing_testbed import BillingTestbed
from tests.billing.test_trial_and_plan import start_trial

PERIOD_DAYS: int = 30


class CostWorld:
    """A client with one paid month, usage and messages in that month."""

    def __init__(self, testbed: BillingTestbed, country: CountryPreset) -> None:
        self.testbed: BillingTestbed = testbed
        owner = testbed.add_user(email="owner@example.com")
        self.business: BusinessDocument = testbed.add_business(owner, country)
        start_trial(testbed, owner, self.business)
        subscription = testbed.subscription(self.business.id)
        self.period_start: Microseconds = testbed.clock.now()
        self.period_end = Microseconds(
            int(self.period_start) + PERIOD_DAYS * MICROSECONDS_PER_DAY
        )
        self.add_invoice(
            InvoiceKind.SERVICE_PERIOD,
            int(subscription.price_minor),
            str(subscription.currency_code),
            self.period_start,
            self.period_end,
        )

    def add_invoice(
        self,
        kind: InvoiceKind,
        amount_minor: int,
        currency: str,
        period_start: Microseconds,
        period_end: Microseconds,
        status: InvoiceStatus = InvoiceStatus.PAID,
    ) -> None:
        self.testbed.invoice_repo.save(
            InvoiceDocument(
                business_id=self.business.id,
                kind=kind,
                description=InvoiceDescription("Call and message handling service"),
                amount_minor=MoneyAmountMinor(amount_minor),
                currency_code=CurrencyCode(currency),
                status=status,
                period_start=period_start,
                period_end=period_end,
            )
        )

    def add_message(
        self,
        conversation_id: ConversationId,
        cost_micro_usd: int,
        created_at: Microseconds | None = None,
    ) -> None:
        moment: Microseconds = created_at or self.at(1)
        self.testbed.message_repo.save(
            MessageDocument(
                conversation_id=conversation_id,
                business_id=self.business.id,
                direction=MessageDirection.OUTBOUND,
                author=MessageAuthor.ASSISTANT,
                text=MessageText("Hello"),
                cost_micro_usd=CostMicroUsd(cost_micro_usd),
                created_at=moment,
                updated_at=moment,
            )
        )

    def at(self, days: float) -> Microseconds:
        return Microseconds(int(self.period_start) + int(days * MICROSECONDS_PER_DAY))

    def record_typical_month(self) -> None:
        business_id: BusinessId = self.business.id
        record = self.testbed.record_usage
        conversation_a, conversation_b, conversation_c = (
            ConversationId(),
            ConversationId(),
            ConversationId(),
        )
        record(
            business_id, UsageKind.VOICE_SECONDS, 18_000, 24_000_000, None, self.at(2)
        )
        record(business_id, UsageKind.WHATSAPP_REPLY, 400, 8_480_000, None, self.at(3))
        record(
            business_id,
            UsageKind.LLM_INPUT_TOKENS,
            40_000,
            3_000_000,
            conversation_a,
            self.at(4),
        )
        record(
            business_id,
            UsageKind.LLM_OUTPUT_TOKENS,
            4_000,
            2_000_000,
            conversation_a,
            self.at(4),
        )
        record(
            business_id,
            UsageKind.LLM_INPUT_TOKENS,
            9_000,
            700_000,
            conversation_c,
            self.at(5),
        )
        record(
            business_id, UsageKind.LLM_INPUT_TOKENS, 1_000, 100_000, None, self.at(5)
        )
        record(business_id, UsageKind.DIALOG, 3, 0, None, self.at(5))
        record(
            business_id,
            UsageKind.VOICE_SECONDS,
            600,
            800_000,
            None,
            self.at(PERIOD_DAYS),
        )
        self.add_message(conversation_a, 2_500_000)
        self.add_message(conversation_a, 2_500_000)
        self.add_message(conversation_b, 1_000_000)
        self.add_message(conversation_c, 600_000)
        self.add_message(conversation_b, 9_000_000, created_at=self.at(-1))

    def report(
        self,
        period_start: Microseconds | None = None,
        period_end: Microseconds | None = None,
    ) -> ClientCostReport:
        return self.testbed.compute_client_cost.run(
            ClientCostQuery(
                business_id=self.business.id,
                period_start=period_start or self.period_start,
                period_end=period_end or self.period_end,
            )
        )


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
