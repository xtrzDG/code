"""Bounded places for conversation turns of one kind in one process."""

import threading
from collections.abc import Callable, Generator
from contextlib import contextmanager

from app.contracts.turn_slots import TurnSlotRegistryContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    RateLimitedError,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.platform.constrained_integers import (
    RetryAfterSeconds,
    TurnSlotCount,
    TurnSlotWaitSeconds,
)

# A customer turn waits for a place as long as for the customer's lock: not
# longer than the inbox lease of the job that carries it.
CUSTOMER_TURN_SLOT_WAIT: TurnSlotWaitSeconds = TurnSlotWaitSeconds(150)
# The owner sees a spinner; past this, "try again in a moment".
TEST_CHAT_SLOT_WAIT: TurnSlotWaitSeconds = TurnSlotWaitSeconds(10)
TEST_CHAT_RETRY_AFTER: RetryAfterSeconds = RetryAfterSeconds(5)


class TurnSlotRegistry(TurnSlotRegistryContract):
    """
    At most `slots` turns at once in this process (a bounded semaphore); a
    turn beyond them waits up to `wait_seconds`, then fails with
    `refusal()`. Places are taken in no particular order.
    """

    def __init__(
        self,
        slots: TurnSlotCount,
        wait_seconds: TurnSlotWaitSeconds,
        refusal: Callable[[], ApplicationError],
    ) -> None:
        self._places: threading.BoundedSemaphore = threading.BoundedSemaphore(
            int(slots)
        )
        self._wait_seconds: TurnSlotWaitSeconds = wait_seconds
        self._refusal: Callable[[], ApplicationError] = refusal

    @contextmanager
    def hold(self) -> Generator[None]:
        if not self._places.acquire(timeout=float(int(self._wait_seconds))):
            raise self._refusal()

        try:
            yield
        finally:
            self._places.release()


def build_customer_turn_slots(settings: AppSettings) -> TurnSlotRegistry:
    """
    Customer turns (every channel's, in a worker): as many as the process
    makes model calls at once (LLM_MAX_CONCURRENCY). A turn takes its place
    before the customer's lock, so turns that wait hold no connection.
    """

    slots = TurnSlotCount(int(settings.llm_max_concurrency))
    return TurnSlotRegistry(
        slots=slots,
        wait_seconds=CUSTOMER_TURN_SLOT_WAIT,
        refusal=lambda: ExternalServiceError(
            f"All {int(slots)} customer turn places of this process stayed "
            f"busy for {int(CUSTOMER_TURN_SLOT_WAIT)} s (LLM_MAX_CONCURRENCY)."
        ),
    )


def build_test_chat_slots(settings: AppSettings) -> TurnSlotRegistry:
    """
    The owners' test chat answers in the request (TEST_CHAT_MAX_CONCURRENCY
    at once per API process), so a few test chats never take the threads
    the cabinet needs; beyond them the owner is asked to try again (429).
    """

    return TurnSlotRegistry(
        slots=TurnSlotCount(int(settings.test_chat_max_concurrency)),
        wait_seconds=TEST_CHAT_SLOT_WAIT,
        refusal=refuse_busy_test_chat,
    )


def refuse_busy_test_chat() -> RateLimitedError:
    """Every test chat place stayed taken: 429, try again in a moment."""

    return RateLimitedError(
        "The test chat is busy right now; try again in a few seconds.",
        retry_after_seconds=TEST_CHAT_RETRY_AFTER,
    )
