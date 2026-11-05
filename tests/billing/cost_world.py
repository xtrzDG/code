"""A paying client with usage, invoices and rates for the client cost tests."""

from typed_time_provider import Microseconds

from app.schemas.constants.billing import InvoiceKind, InvoiceStatus, UsageKind
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.billing_ledger import ClientCostQuery, ClientCostReport
from app.schemas.typings.billing.constrained_integers import (
    CostMicroUsd,
    MoneyAmountMinor,
)
from app.schemas.typings.billing.strings import InvoiceDescription
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from tests.billing.billing_settings import MICROSECONDS_PER_DAY, CountryPreset
from tests.billing.billing_testbed import BillingTestbed
from tests.billing.plan_steps import start_trial

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
