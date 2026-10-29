"""Places for the landing page's demo turns in one API process."""

from app.registries.turns.turn_slot_registry import TurnSlotRegistry
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.platform.constrained_integers import (
    RetryAfterSeconds,
    TurnSlotCount,
    TurnSlotWaitSeconds,
)

# Visitors wait for each answer in the request: two at a time per process
# keep the cabinet's threads and the model budget for the paying owners.
PUBLIC_DEMO_SLOTS: TurnSlotCount = TurnSlotCount(2)
PUBLIC_DEMO_SLOT_WAIT: TurnSlotWaitSeconds = TurnSlotWaitSeconds(8)
PUBLIC_DEMO_RETRY_AFTER: RetryAfterSeconds = RetryAfterSeconds(5)


def build_public_demo_slots() -> TurnSlotRegistry:
    """At most two demo turns at once; the next visitor waits up to 8 s."""

    return TurnSlotRegistry(
        slots=PUBLIC_DEMO_SLOTS,
        wait_seconds=PUBLIC_DEMO_SLOT_WAIT,
        refusal=refuse_busy_public_demo,
    )


def refuse_busy_public_demo() -> RateLimitedError:
    """Every demo place stayed taken: 429, try again in a moment."""

    return RateLimitedError(
        "The demo assistants are busy; try again in a moment.",
        retry_after_seconds=PUBLIC_DEMO_RETRY_AFTER,
    )
