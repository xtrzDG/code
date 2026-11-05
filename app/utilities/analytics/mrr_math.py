"""
Monthly recurring revenue from the billing steps: each SUBSCRIBED,
PLAN_CHANGED and CANCELLED event carries what the subscription brings a
month after it, so replaying a business's events gives its MRR at any
moment and every movement, in euros.
"""

from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from typed_time_provider import Microseconds

from app.schemas.constants.analytics import MrrMovementKind, ProductEventName
from app.schemas.domain.product_events import ProductEventDocument
from app.schemas.dto.analytics.revenue_views import MrrMovementView, MrrView
from app.schemas.dto.billing import Money
from app.schemas.typings.analytics.constrained_integers import AccountCount
from app.schemas.typings.analytics.integers import MrrChangeMinor
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import CurrencyCode

EUR: CurrencyCode = CurrencyCode("EUR")
BILLING_EVENTS: tuple[ProductEventName, ...] = (
    ProductEventName.SUBSCRIBED,
    ProductEventName.PLAN_CHANGED,
    ProductEventName.CANCELLED,
)
# Minor units of a currency -> euro cents; None without an official rate.
type EuroConverter = Callable[[int, CurrencyCode], int | None]


@dataclass
class RevenueState:
    """One business while its billing steps are replayed."""

    is_paying: bool = False
    has_paid: bool = False
    amount: int = 0


@dataclass
class MovementTally:
    amounts: dict[MrrMovementKind, int] = field(
        default_factory=lambda: dict.fromkeys(MrrMovementKind, 0)
    )
    accounts: dict[MrrMovementKind, set[BusinessId]] = field(
        default_factory=lambda: {kind: set() for kind in MrrMovementKind}
    )

    def add(self, kind: MrrMovementKind, amount: int, business: BusinessId) -> None:
        self.amounts[kind] += amount
        self.accounts[kind].add(business)


def apply_step(
    state: RevenueState,
    name: ProductEventName,
    amount: int,
) -> list[tuple[MrrMovementKind, int]]:
    """Replay one billing step; the movements it made (positive amounts)."""

    movements: list[tuple[MrrMovementKind, int]] = []
    if name is ProductEventName.CANCELLED:
        if state.is_paying:
            movements.append((MrrMovementKind.CHURN, state.amount))
            state.is_paying = False
        return movements

    if name is ProductEventName.SUBSCRIBED and not state.is_paying:
        kind = MrrMovementKind.REACTIVATION if state.has_paid else MrrMovementKind.NEW
        movements.append((kind, amount))
        state.is_paying = state.has_paid = True
    elif state.is_paying and amount > state.amount:
        movements.append((MrrMovementKind.EXPANSION, amount - state.amount))
    elif state.is_paying and amount < state.amount:
        movements.append((MrrMovementKind.CONTRACTION, state.amount - amount))

    state.amount = amount
    return movements


def euro_amount(event: ProductEventDocument, to_eur: EuroConverter) -> int | None:
    """What the step says the subscription brings a month, in euro cents."""

    facts = event.properties
    if facts.monthly_amount is None or facts.currency_code is None:
        return 0

    return to_eur(int(facts.monthly_amount), facts.currency_code)


def build_mrr(
    events: Sequence[ProductEventDocument],
    in_scope: set[BusinessId],
    period_start: Microseconds,
    period_end: Microseconds,
    to_eur: EuroConverter,
) -> MrrView:
    """
    MRR at the start and the end of the period over the businesses in
    scope, and the movements in between; a business whose currency has no
    rate to euros is left out (and its currency named).
    """

    by_business: dict[BusinessId, list[ProductEventDocument]] = defaultdict(list)
    for event in sorted(events, key=lambda item: (int(item.occurred_at), item.id)):
        business_id = event.business_id
        if business_id is None or event.name not in BILLING_EVENTS:
            continue
        if business_id in in_scope:
            by_business[business_id].append(event)

    start_total = end_total = paying = 0
    tally = MovementTally()
    unconverted: set[CurrencyCode] = set()
    for business_id, steps in by_business.items():
        amounts = [euro_amount(step, to_eur) for step in steps]
        if any(amount is None for amount in amounts):
            unconverted.update(
                step.properties.currency_code
                for step, amount in zip(steps, amounts, strict=True)
                if amount is None and step.properties.currency_code is not None
            )
            continue

        state = RevenueState()
        start_amount: int | None = None
        for step, amount in zip(steps, amounts, strict=True):
            if int(step.occurred_at) >= int(period_end):
                break

            if start_amount is None and int(step.occurred_at) >= int(period_start):
                start_amount = state.amount if state.is_paying else 0

            for kind, moved in apply_step(state, step.name, amount or 0):
                if start_amount is not None:
                    tally.add(kind, moved, business_id)

        if start_amount is None:
            start_amount = state.amount if state.is_paying else 0

        start_total += start_amount
        end_total += state.amount if state.is_paying else 0
        paying += 1 if state.is_paying else 0

    return MrrView(
        start=euros(start_total),
        end=euros(end_total),
        net_change=MrrChangeMinor(end_total - start_total),
        movements=[
            MrrMovementView(
                kind=kind,
                amount=euros(tally.amounts[kind]),
                accounts=AccountCount(len(tally.accounts[kind])),
            )
            for kind in MrrMovementKind
        ],
        paying_accounts=AccountCount(paying),
        arpa=None if paying == 0 else euros((end_total + paying // 2) // paying),
        unconverted_currencies=sorted(unconverted, key=str),
    )


def paying_businesses_at(
    events: Sequence[ProductEventDocument], at: Microseconds
) -> set[BusinessId]:
    """The businesses that pay for a subscription at a moment."""

    states: dict[BusinessId, RevenueState] = defaultdict(RevenueState)
    for event in sorted(events, key=lambda item: (int(item.occurred_at), item.id)):
        if event.business_id is None or event.name not in BILLING_EVENTS:
            continue
        if int(event.occurred_at) > int(at):
            break

        apply_step(states[event.business_id], event.name, 0)

    return {business for business, state in states.items() if state.is_paying}


def euros(cents: int) -> Money:
    return Money(amount_minor=MoneyAmountMinor(cents), currency_code=EUR)
