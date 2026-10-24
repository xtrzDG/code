"""
Rules of the inbox and the outbox that need no store: which send errors
are tried again and when, what a platform's Retry-After means, which ids
an inbox row is recognised by, and how job payloads are read.
"""

from collections.abc import Callable

import pytest

from app.schemas.constants.deliveries import DeliveryFailureKind
from app.schemas.exceptions.application_errors import (
    ChannelCredentialRejectedError,
    DeliveryNotConfiguredError,
    ExternalServiceError,
    NotFoundError,
    ProviderRateLimitedError,
    ProviderRejectedMessageError,
    ValidationFailedError,
    WhatsAppTemplateRejectedError,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.deliveries.constrained_integers import DeliveryAttemptCount
from app.schemas.typings.platform.constrained_integers import RetryAfterSeconds
from app.schemas.typings.platform.strings import JobPayloadJson
from app.utilities.channels.retry_after import read_retry_after_seconds
from app.utilities.deliveries.delivery_jobs import (
    decode_inbound_event_payload,
    decode_outbound_message_payload,
)
from app.utilities.deliveries.delivery_keys import bounded_provider_message_id
from app.utilities.deliveries.inbound_failures import (
    describe_inbound_error,
    is_final_inbound_failure,
    is_inbound_refusal,
)
from app.utilities.deliveries.retry_policy import (
    MAX_DELIVERY_ATTEMPTS,
    RETRY_MAX_SECONDS,
    classify_delivery_error,
    describe_delivery_error,
    is_retryable,
    read_retry_after,
    retry_delay_seconds,
)

NO_JITTER: float = 0.5


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (ProviderRateLimitedError("slow down"), DeliveryFailureKind.RATE_LIMITED),
        (
            ChannelCredentialRejectedError("revoked"),
            DeliveryFailureKind.CREDENTIAL_REJECTED,
        ),
        (DeliveryNotConfiguredError("no email"), DeliveryFailureKind.NOT_CONFIGURED),
        (ProviderRejectedMessageError("blocked"), DeliveryFailureKind.REJECTED),
        (WhatsAppTemplateRejectedError("template"), DeliveryFailureKind.REJECTED),
        (ExternalServiceError("500"), DeliveryFailureKind.TRANSIENT),
        (NotFoundError("Channel was not found."), DeliveryFailureKind.REJECTED),
    ],
)
def test_send_errors_are_sorted_by_what_a_later_attempt_can_do(
    error: ApplicationError, expected: DeliveryFailureKind
) -> None:
    assert classify_delivery_error(error) is expected


def test_only_temporary_failures_are_tried_again_and_only_until_the_last_attempt() -> (
    None
):
    last: DeliveryAttemptCount = MAX_DELIVERY_ATTEMPTS

    assert is_retryable(DeliveryFailureKind.TRANSIENT, DeliveryAttemptCount(1))
    assert is_retryable(DeliveryFailureKind.RATE_LIMITED, DeliveryAttemptCount(7))
    assert not is_retryable(DeliveryFailureKind.TRANSIENT, last)
    assert not is_retryable(DeliveryFailureKind.REJECTED, DeliveryAttemptCount(1))
    assert not is_retryable(
        DeliveryFailureKind.CREDENTIAL_REJECTED, DeliveryAttemptCount(1)
    )


def test_backoff_doubles_with_a_cap_and_jitter_moves_it_by_a_quarter() -> None:
    assert retry_delay_seconds(DeliveryAttemptCount(1), None, NO_JITTER) == 10
    assert retry_delay_seconds(DeliveryAttemptCount(2), None, NO_JITTER) == 20
    assert retry_delay_seconds(DeliveryAttemptCount(4), None, NO_JITTER) == 80
    assert (
        retry_delay_seconds(DeliveryAttemptCount(30), None, NO_JITTER)
        == RETRY_MAX_SECONDS
    )
    assert retry_delay_seconds(DeliveryAttemptCount(1), None, 0.0) == 8
    assert retry_delay_seconds(DeliveryAttemptCount(1), None, 1.0) == 12
    assert retry_delay_seconds(DeliveryAttemptCount(1), None, 7.0) == 12


def test_a_platforms_retry_after_is_never_cut_short() -> None:
    error = ProviderRateLimitedError("429", retry_after_seconds=RetryAfterSeconds(120))

    assert read_retry_after(error) == 120
    assert read_retry_after(ExternalServiceError("500")) is None
    assert (
        retry_delay_seconds(DeliveryAttemptCount(1), read_retry_after(error), 0.0)
        == 120
    )
    assert (
        retry_delay_seconds(DeliveryAttemptCount(8), RetryAfterSeconds(5), NO_JITTER)
        == 1280
    )


def test_retry_after_comes_from_the_body_or_a_header_in_seconds() -> None:
    assert read_retry_after_seconds(30, "90") == 30
    assert read_retry_after_seconds(None, " 90 ") == 90
    assert read_retry_after_seconds(None, "Wed, 21 Oct 2026 07:28:00 GMT") is None
    assert read_retry_after_seconds(None, None) is None
    assert read_retry_after_seconds(0, None) == 1
    assert read_retry_after_seconds(10**9, None) == 24 * 60 * 60


def test_stored_errors_are_one_short_line() -> None:
    long_error = ExternalServiceError("word " * 400)

    assert describe_delivery_error(ExternalServiceError("a\n  b")) == "a b"
    assert describe_delivery_error(ExternalServiceError()) == "ExternalServiceError"
    assert len(describe_delivery_error(long_error)) == 500
    assert str(describe_delivery_error(long_error)).endswith("…")
    assert len(describe_inbound_error(RuntimeError("x" * 900))) == 500
    assert describe_inbound_error(RuntimeError()) == "RuntimeError"


def test_inbox_failures_end_on_a_refusal_or_on_the_last_attempt() -> None:
    assert is_inbound_refusal(ValidationFailedError("bad"))
    assert not is_inbound_refusal(ExternalServiceError("500"))
    assert not is_inbound_refusal(RuntimeError("crash"))
    assert is_final_inbound_failure(
        ValidationFailedError("bad"), is_final_attempt=False
    )
    assert not is_final_inbound_failure(RuntimeError("crash"), is_final_attempt=False)
    assert is_final_inbound_failure(RuntimeError("crash"), is_final_attempt=True)


def test_a_message_without_a_usable_platform_id_gets_a_local_one() -> None:
    kept = ProviderMessageId("wamid.1")

    assert bounded_provider_message_id(kept) == kept
    assert str(bounded_provider_message_id(None)).startswith("local:")
    assert str(bounded_provider_message_id(ProviderMessageId("  "))).startswith(
        "local:"
    )
    assert str(bounded_provider_message_id(ProviderMessageId("x" * 600))).startswith(
        "local:"
    )


@pytest.mark.parametrize(
    "decode", [decode_inbound_event_payload, decode_outbound_message_payload]
)
def test_job_payloads_that_name_no_row_are_refused(
    decode: Callable[[JobPayloadJson], object],
) -> None:
    with pytest.raises(ValidationFailedError):
        decode(JobPayloadJson('{"something": "else"}'))
