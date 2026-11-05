"""How long a messaging platform asked us to wait before sending again."""

from app.schemas.typings.platform.constrained_integers import RetryAfterSeconds

MIN_RETRY_AFTER_SECONDS: int = 1
MAX_RETRY_AFTER_SECONDS: int = 24 * 60 * 60


def read_retry_after_seconds(
    body_seconds: int | None,
    header_value: str | None,
) -> RetryAfterSeconds | None:
    """
    The pause from the response body (Telegram `parameters.retry_after`)
    or else the Retry-After header in seconds (an HTTP date is ignored),
    kept within one second and one day; None when neither names one.
    """

    seconds: int | None = body_seconds
    if seconds is None and header_value is not None:
        text: str = header_value.strip()
        seconds = int(text) if text.isdigit() else None

    if seconds is None:
        return None

    return RetryAfterSeconds(
        min(max(seconds, MIN_RETRY_AFTER_SECONDS), MAX_RETRY_AFTER_SECONDS)
    )
