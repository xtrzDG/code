"""
When an outbox message is tried again: backoff with jitter after a
temporary failure (longer when the platform asked for a pause), never
after a refusal, and not at all after the last attempt.
"""

from app.schemas.constants.deliveries import DeliveryFailureKind
from app.schemas.exceptions.application_errors import (
    ChannelCredentialRejectedError,
    DeliveryNotConfiguredError,
    ExternalServiceError,
    ProviderRateLimitedError,
    ProviderRejectedMessageError,
    WhatsAppTemplateRejectedError,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.deliveries.constrained_integers import DeliveryAttemptCount
from app.schemas.typings.deliveries.strings import DeliveryErrorText
from app.schemas.typings.platform.constrained_integers import RetryAfterSeconds

# 10 s, 20 s, 40 s ... up to 30 minutes; the 8th failed attempt (about 21
# minutes after the first) is the last.
MAX_DELIVERY_ATTEMPTS: DeliveryAttemptCount = DeliveryAttemptCount(8)
RETRY_BASE_SECONDS: int = 10
RETRY_MAX_SECONDS: int = 30 * 60
# Each delay is moved by up to a quarter either way, so messages that failed
# together (a platform outage) do not all come back at the same second.
JITTER_SHARE: float = 0.25
MAX_ERROR_TEXT_LENGTH: int = 500
RETRYABLE_FAILURES: frozenset[DeliveryFailureKind] = frozenset(
    {DeliveryFailureKind.RATE_LIMITED, DeliveryFailureKind.TRANSIENT}
)


def classify_delivery_error(error: ApplicationError) -> DeliveryFailureKind:
    """What a send error means for the next attempt."""

    if isinstance(error, ProviderRateLimitedError):
        return DeliveryFailureKind.RATE_LIMITED

    if isinstance(error, ChannelCredentialRejectedError):
        return DeliveryFailureKind.CREDENTIAL_REJECTED

    if isinstance(error, DeliveryNotConfiguredError):
        return DeliveryFailureKind.NOT_CONFIGURED

    if isinstance(error, ProviderRejectedMessageError | WhatsAppTemplateRejectedError):
        return DeliveryFailureKind.REJECTED

    if isinstance(error, ExternalServiceError):
        return DeliveryFailureKind.TRANSIENT

    # Not a provider failure (the channel is gone, a value is invalid):
    # sending the same message again cannot help.
    return DeliveryFailureKind.REJECTED


def read_retry_after(error: ApplicationError) -> RetryAfterSeconds | None:
    if isinstance(error, ProviderRateLimitedError):
        return error.retry_after_seconds

    return None


def is_retryable(
    failure: DeliveryFailureKind,
    attempts: DeliveryAttemptCount,
) -> bool:
    """Another attempt follows a temporary failure until the last one."""

    return failure in RETRYABLE_FAILURES and int(attempts) < int(
        MAX_DELIVERY_ATTEMPTS
    )


def retry_delay_seconds(
    attempts: DeliveryAttemptCount,
    retry_after: RetryAfterSeconds | None,
    jitter_fraction: float,
) -> int:
    """
    Seconds until the next attempt after `attempts` failed ones:
    exponential backoff with jitter (`jitter_fraction` in [0, 1), 0.5 means
    none), never sooner than the platform's Retry-After.
    """

    exponent: int = max(0, int(attempts) - 1)
    backoff: float = min(RETRY_BASE_SECONDS * (2**exponent), RETRY_MAX_SECONDS)
    bounded_fraction: float = min(max(jitter_fraction, 0.0), 1.0)
    jittered: float = backoff * (1 + JITTER_SHARE * (2 * bounded_fraction - 1))
    delay: int = max(1, round(jittered))
    if retry_after is not None:
        delay = max(delay, int(retry_after))

    return delay


def describe_delivery_error(error: ApplicationError) -> DeliveryErrorText:
    """The error on one line, cut to a stored length."""

    text: str = " ".join(str(error).split()) or type(error).__name__
    if len(text) > MAX_ERROR_TEXT_LENGTH:
        text = text[: MAX_ERROR_TEXT_LENGTH - 1].rstrip() + "…"

    return DeliveryErrorText(text)
