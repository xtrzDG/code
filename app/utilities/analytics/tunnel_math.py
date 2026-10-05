"""
Where the setup tunnel loses people, counted per unit: an owner (the owners'
tunnel) or a business (the business tunnel, a setup that has not created
its business yet counting once too).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from app.schemas.constants.analytics import ProductEventName, TunnelStepKey


@dataclass(frozen=True)
class TunnelUnit:
    """One unit's tunnel screens by what happened, and whether it went live."""

    key: str
    tunnel: Mapping[ProductEventName, frozenset[TunnelStepKey]] = field(
        default_factory=dict[ProductEventName, frozenset[TunnelStepKey]]
    )
    is_live: bool = False


@dataclass(frozen=True)
class TunnelCounts:
    """Units that entered a screen, went on from it, skipped it, stopped there."""

    step: TunnelStepKey
    entered: int
    completed: int
    skipped: int
    stopped_here: int


def count_tunnel(units: Sequence[TunnelUnit]) -> list[TunnelCounts]:
    """
    Per tunnel screen: units that entered it, completed it (went on without
    skipping), skipped it, and stopped there: it is the furthest screen
    they entered and they never went live.
    """

    order: list[TunnelStepKey] = list(TunnelStepKey)
    stopped: dict[TunnelStepKey, int] = dict.fromkeys(order, 0)
    for unit in units:
        entered = unit.tunnel.get(ProductEventName.TUNNEL_STEP_ENTERED, frozenset())
        if entered and not unit.is_live:
            stopped[max(entered, key=order.index)] += 1

    def units_with(name: ProductEventName, step: TunnelStepKey) -> set[str]:
        return {
            unit.key for unit in units if step in unit.tunnel.get(name, frozenset())
        }

    counts: list[TunnelCounts] = []
    for step in order:
        skipped = units_with(ProductEventName.TUNNEL_STEP_SKIPPED, step)
        completed = units_with(ProductEventName.TUNNEL_STEP_COMPLETED, step) - skipped
        counts.append(
            TunnelCounts(
                step=step,
                entered=len(units_with(ProductEventName.TUNNEL_STEP_ENTERED, step)),
                completed=len(completed),
                skipped=len(skipped),
                stopped_here=stopped[step],
            )
        )

    return counts
