"""
What the connection pool reports about itself: how long threads wait for
a connection and how many are in use (service metrics), and the cursor
class whose statements become spans when tracing is on.
"""

from dataclasses import dataclass

from app.clients.postgres.traced_cursor import TracedCursorClass
from app.contracts.service_metrics import ServiceMetricsContract
from app.schemas.typings.observability.constrained_floats import ObservedSeconds
from app.utilities.observability.metrics.null_service_metrics import (
    NO_SERVICE_METRICS,
)


@dataclass(frozen=True)
class PoolInstruments:
    """The pool's metrics and the cursor class of its connections (None: plain)."""

    metrics: ServiceMetricsContract = NO_SERVICE_METRICS
    cursor_class: TracedCursorClass | None = None

    def connection_taken(self, wait_seconds: float) -> None:
        self.metrics.observe_pool_wait(ObservedSeconds(max(0.0, wait_seconds)))
        self.metrics.count_pool_connection_taken()

    def connection_returned(self) -> None:
        self.metrics.count_pool_connection_returned()


NO_POOL_INSTRUMENTS: PoolInstruments = PoolInstruments()
