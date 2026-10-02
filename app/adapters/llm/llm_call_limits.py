"""The per-call timeout and retries of a request, as the provider clients take them."""

from app.schemas.dto.conversations import LlmRequest


def call_timeout_seconds(request: LlmRequest) -> float | None:
    """Seconds this call may take; None keeps the client's default."""

    if request.call_limits is None:
        return None

    return float(int(request.call_limits.timeout_seconds))


def call_max_retries(request: LlmRequest) -> int | None:
    """Retries of this call; None keeps the client's default."""

    if request.call_limits is None:
        return None

    return int(request.call_limits.retry_limit)
