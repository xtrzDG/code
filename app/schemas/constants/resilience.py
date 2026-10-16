from enum import StrEnum


class CircuitState(StrEnum):
    """
    A circuit breaker's state: CLOSED lets calls through and counts their
    failures; OPEN refuses calls until its wait is over; HALF_OPEN lets one
    trial call through, whose outcome closes or opens the circuit again.
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
