from collections import defaultdict
from decimal import Decimal

from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
    UsageEventRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.conversation_repositories import MessageRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import InvoiceStatus
from app.schemas.domain.billing import (
    SubscriptionDocument,
    UsageEventDocument,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.billing import Money
from app.schemas.dto.billing_ledger import (
    ClientCostQuery,
    ClientCostReport,
    MarginMoney,
    UsageCostLine,
)
from app.schemas.dto.catalog.plan_quotes import ExchangeRateQuote
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.billing.constrained_floats import GrossMarginPercent
from app.schemas.typings.billing.constrained_integers import (
    CostMicroUsd,
    MoneyAmountMinor,
)
from app.schemas.typings.billing.integers import MarginAmountMinor
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.use_cases.billing.planned_provider_costs import (
    PLANNED_MONTHLY_PROVIDER_COSTS,
)
from app.use_cases.shared.billing_records import find_current_subscription
from app.utilities.billing.client_cost_math import (
    LLM_USAGE_KINDS,
    MICRO_UNITS_PER_UNIT,
    PROVIDER_COST_CURRENCY,
    compute_margin_percent,
    compute_period_share,
    convert_amount,
    summarize_usage_costs,
    to_minor_units,
)
from app.utilities.money.money_math import get_currency_minor_unit_digits

type ConversationKey = ConversationId | None


class ComputeClientCostUseCase(UseCaseContract[ClientCostQuery, ClientCostReport]):
    """
    Provider cost against revenue of one client for a period (admin view).

    Cost: usage events of the period by kind; the language model spend is
    stored twice by the conversation engine (on each message and as token
    usage events), so per conversation it is counted once - the larger of
    the two records, so that neither a missing message nor a missing event
    hides spend. Revenue: paid invoices prorated by the share of their
    service period inside the window (a setup fee counts when invoiced), in
    the subscription currency. The USD cost is converted with the newest
    dated rate (published, inverse or a cross rate through the euro, shown
    with its date and source); without one, the money cost and the margin
    stay empty rather than invented.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
        usage_event_repo: UsageEventRepoContract,
        message_repo: MessageRepoContract,
        exchange_rate_registry: ExchangeRateRegistryContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._usage_event_repo: UsageEventRepoContract = usage_event_repo
        self._message_repo: MessageRepoContract = message_repo
        self._exchange_rate_registry: ExchangeRateRegistryContract = (
            exchange_rate_registry
        )

    def run(self, input_data: ClientCostQuery) -> ClientCostReport:
        if input_data.period_end <= input_data.period_start:
            raise ValidationFailedError("The cost period must end after it starts.")

        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        subscription: SubscriptionDocument | None = find_current_subscription(
            self._subscription_repo,
            business.id,
        )
        report_currency: CurrencyCode = (
            business.currency_code
            if subscription is None
            else subscription.currency_code
        )
        events: list[UsageEventDocument] = (
            self._usage_event_repo.list_by_business_between(
                business.id,
                input_data.period_start,
                input_data.period_end,
            )
        )
        usage_cost_lines: list[UsageCostLine] = summarize_usage_costs(events)
        llm_cost: int = self._reconcile_llm_cost(business, events, input_data)
        provider_cost_micro_usd: int = llm_cost + sum(
            int(line.cost_micro_usd)
            for line in usage_cost_lines
            if line.kind not in LLM_USAGE_KINDS
        )
        revenue_minor: int = self._compute_revenue_minor(
            business,
            report_currency,
            input_data,
        )
        provider_cost: Money | None = None
        margin: MarginMoney | None = None
        margin_percent: GrossMarginPercent | None = None
        conversion: tuple[Decimal, ExchangeRateQuote | None] | None = convert_amount(
            Decimal(provider_cost_micro_usd) / MICRO_UNITS_PER_UNIT,
            PROVIDER_COST_CURRENCY,
            report_currency,
            self._exchange_rate_registry,
        )
        exchange_rate: ExchangeRateQuote | None = None
        if conversion is not None:
            cost_major, exchange_rate = conversion
            cost_minor: int = to_minor_units(cost_major, report_currency)
            provider_cost = Money(
                amount_minor=MoneyAmountMinor(cost_minor),
                currency_code=report_currency,
            )
            margin = MarginMoney(
                amount_minor=MarginAmountMinor(revenue_minor - cost_minor),
                currency_code=report_currency,
            )
            margin_percent = compute_margin_percent(revenue_minor, cost_minor)

        plan_key = business.plan_key if subscription is None else subscription.plan_key
        return ClientCostReport(
            business_id=business.id,
            period_start=input_data.period_start,
            period_end=input_data.period_end,
            usage_cost_lines=usage_cost_lines,
            llm_cost_micro_usd=CostMicroUsd(llm_cost),
            provider_cost_micro_usd=CostMicroUsd(provider_cost_micro_usd),
            revenue=Money(
                amount_minor=MoneyAmountMinor(revenue_minor),
                currency_code=report_currency,
            ),
            provider_cost=provider_cost,
            margin=margin,
            margin_percent=margin_percent,
            exchange_rate=exchange_rate,
            planned_monthly_provider_cost=PLANNED_MONTHLY_PROVIDER_COSTS.get(plan_key),
        )

    def _reconcile_llm_cost(
        self,
        business: BusinessDocument,
        events: list[UsageEventDocument],
        input_data: ClientCostQuery,
    ) -> int:
        usage_costs: defaultdict[ConversationKey, int] = defaultdict(int)
        for event in events:
            if event.kind in LLM_USAGE_KINDS:
                usage_costs[event.conversation_id] += int(event.cost_micro_usd)

        message_costs: defaultdict[ConversationKey, int] = defaultdict(int)
        for conversation_id, cost in self._message_repo.sum_cost_by_conversation(
            business.id, input_data.period_start, input_data.period_end
        ).items():
            message_costs[conversation_id] += int(cost)

        unattributed: int = usage_costs.pop(None, 0) + message_costs.pop(None, 0)
        conversation_ids: set[ConversationKey] = set(usage_costs) | set(message_costs)
        return unattributed + sum(
            max(usage_costs[conversation_id], message_costs[conversation_id])
            for conversation_id in conversation_ids
        )

    def _compute_revenue_minor(
        self,
        business: BusinessDocument,
        report_currency: CurrencyCode,
        input_data: ClientCostQuery,
    ) -> int:
        revenue: Decimal = Decimal(0)
        for invoice in self._invoice_repo.list_by_business(business.id):
            if invoice.status is not InvoiceStatus.PAID:
                continue

            share: Decimal = compute_period_share(invoice, input_data)
            if share == 0:
                continue

            amount_major: Decimal = Decimal(int(invoice.amount_minor)).scaleb(
                -int(get_currency_minor_unit_digits(invoice.currency_code))
            )
            conversion: tuple[Decimal, ExchangeRateQuote | None] | None = (
                convert_amount(
                    amount_major,
                    invoice.currency_code,
                    report_currency,
                    self._exchange_rate_registry,
                )
            )
            if conversion is not None:
                revenue += conversion[0] * share

        return to_minor_units(revenue, report_currency)
