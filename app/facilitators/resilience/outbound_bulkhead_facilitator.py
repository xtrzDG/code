import threading
from collections.abc import Generator
from contextlib import contextmanager

from app.contracts.resilience import OutboundBulkheadContract
from app.schemas.constants.resilience import OutboundProvider
from app.schemas.typings.resilience.booleans import IsProviderSlotTaken
from app.schemas.typings.resilience.constrained_integers import ProviderSlotCount


class OutboundBulkheadFacilitator(OutboundBulkheadContract):
    """
    The bulkheads of a worker's outbound lane: every provider may have at
    most `slots_per_provider` sends in flight in this process (half of the
    lane's threads by default: 2 of 4). A send that finds its provider's
    slots taken does not wait for one, so a provider that hangs for its
    whole timeout holds at most its own slots, and the other threads keep
    sending through the other providers. Thread-safe; each process counts
    its own sends.
    """

    def __init__(self, slots_per_provider: ProviderSlotCount) -> None:
        self._semaphores: dict[OutboundProvider, threading.BoundedSemaphore] = {
            provider: threading.BoundedSemaphore(int(slots_per_provider))
            for provider in OutboundProvider
        }

    @contextmanager
    def reserve(self, provider: OutboundProvider) -> Generator[IsProviderSlotTaken]:
        semaphore: threading.BoundedSemaphore = self._semaphores[provider]
        if not semaphore.acquire(blocking=False):
            yield False
            return

        try:
            yield True
        finally:
            semaphore.release()
