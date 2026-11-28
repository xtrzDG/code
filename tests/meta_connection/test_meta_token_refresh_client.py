"""
Renewing a WhatsApp Embedded Signup token: how Meta's refusals and failures
reach the caller (never with the app secret, a token or the request's
address, neither in the error nor in the processes' log), and the renewal
behind Meta's circuit breaker.
"""

import io
import logging
from collections.abc import Iterator

import httpx
import pytest

from app.adapters.channels.circuit_breaking_meta_token_refresh_adapter import (
    CircuitBreakingMetaTokenRefreshAdapter,
)
from app.clients.meta.meta_oauth_client import MetaOAuthClient
from app.facilitators.resilience.circuit_breaker_facilitator import (
    CircuitBreakerFacilitator,
)
from app.schemas.constants.observability import LogFormat
from app.schemas.constants.resilience import CircuitState, OutboundProvider
from app.schemas.dto.channels.meta_provider import MetaAppCredentials
from app.schemas.exceptions.application_errors import (
    ChannelCredentialRejectedError,
    ExternalServiceError,
    ProviderCircuitOpenError,
    ProviderRateLimitedError,
    ProviderRejectedMessageError,
    ValidationFailedError,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.meta_connection.strings import MetaAccessToken
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret
from app.utilities.observability.logging_setup import (
    QUIET_LOGGER_NAMES,
    UVICORN_LOGGER_NAMES,
    configure_logging,
)
from app.utilities.resilience.provider_circuits import provider_circuit
from tests.channels.recording_transport import RecordingTransport
from tests.resilience.test_circuit_breaker import Ticks

APP = MetaAppCredentials(
    app_id=PlatformIdentifier("1234567890"),
    app_secret=PlatformSecret("test-app-secret-0000"),
)
TOKEN = MetaAccessToken("EAAfake-token-1")
META = provider_circuit(OutboundProvider.META)
TOKEN_PATH: str = r"/oauth/access_token$"
# What must never be written: the secret, the tokens, the request's address.
SECRETS: tuple[str, ...] = (
    "test-app-secret-0000",
    "EAAfake-token-1",
    "EAAfake-token-2",
    "client_secret",
    "graph.facebook.com",
    "oauth/access_token",
)


def graph_error(code: int, message: str) -> dict[str, object]:
    return {
        "error": {
            "message": message,
            "type": "OAuthException",
            "code": code,
            "fbtrace_id": "AbCdEfGhIjK0000",
        }
    }


def assert_nothing_secret(text: str) -> None:
    assert [secret for secret in SECRETS if secret in text] == []


def refresh(graph: RecordingTransport) -> MetaAccessToken:
    return MetaOAuthClient(transport=graph.build()).refresh_business_token(TOKEN, APP)


def answering(status: int, body: dict[str, object]) -> RecordingTransport:
    graph = RecordingTransport()
    graph.respond("GET", TOKEN_PATH, body, status)
    return graph


def failing_transport() -> httpx.MockTransport:
    def fail(request: httpx.Request) -> httpx.Response:
        # httpx errors may name the address, query string and all.
        raise httpx.ConnectTimeout(f"timed out reaching {request.url}", request=request)

    return httpx.MockTransport(fail)


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        # The token expired, was revoked or is not one Meta renews.
        (
            400,
            graph_error(190, "Error validating access token."),
            ValidationFailedError,
        ),
        (400, graph_error(100, "Invalid parameter"), ValidationFailedError),
        (401, {}, ChannelCredentialRejectedError),
        (403, graph_error(10, "Permission denied"), ChannelCredentialRejectedError),
        (400, graph_error(10, "Permission denied"), ProviderRejectedMessageError),
        (429, {}, ProviderRateLimitedError),
        (
            400,
            graph_error(4, "Application request limit reached"),
            ProviderRateLimitedError,
        ),
        (500, graph_error(1, "An unknown error occurred"), ExternalServiceError),
        # Meta answered without a new token.
        (200, {"token_type": "bearer", "expires_in": 5183944}, ExternalServiceError),
    ],
    ids=["190", "100", "401", "403", "400-other", "429", "code-4", "500", "no-token"],
)
def test_meta_s_answers_become_application_errors(
    status: int, body: dict[str, object], expected: type[ApplicationError]
) -> None:
    with pytest.raises(ApplicationError) as raised:
        refresh(answering(status, body))

    assert type(raised.value) is expected
    assert_nothing_secret(str(raised.value))


def test_an_unreachable_meta_never_names_the_address_or_the_secret() -> None:
    client = MetaOAuthClient(transport=failing_transport())

    with pytest.raises(ExternalServiceError) as raised:
        client.refresh_business_token(TOKEN, APP)

    assert type(raised.value) is ExternalServiceError
    assert_nothing_secret(str(raised.value))
    # The transport's error (with the address in it) is not chained along.
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__ is True


@pytest.fixture
def process_log() -> Iterator[io.StringIO]:
    """The API's and workers' logging (`configure_logging`), put back after."""

    root: logging.Logger = logging.getLogger()
    handlers: list[logging.Handler] = list(root.handlers)
    root_level: int = root.level
    quiet_levels: dict[str, int] = {
        name: logging.getLogger(name).level for name in QUIET_LOGGER_NAMES
    }
    uvicorn_state: dict[str, tuple[list[logging.Handler], bool]] = {
        name: (
            list(logging.getLogger(name).handlers),
            logging.getLogger(name).propagate,
        )
        for name in UVICORN_LOGGER_NAMES
    }
    stream = io.StringIO()
    configure_logging(LogFormat.TEXT, level=logging.DEBUG, stream=stream)
    try:
        yield stream
    finally:
        root.handlers = handlers
        root.setLevel(root_level)
        for name, level in quiet_levels.items():
            logging.getLogger(name).setLevel(level)
        for name, (uvicorn_handlers, propagate) in uvicorn_state.items():
            logging.getLogger(name).handlers = uvicorn_handlers
            logging.getLogger(name).propagate = propagate


def test_the_processes_log_neither_the_secret_nor_the_tokens(
    process_log: io.StringIO,
) -> None:
    graph = RecordingTransport()
    graph.respond("GET", TOKEN_PATH, {"access_token": "EAAfake-token-2"})
    refresh(graph)
    graph.respond("GET", TOKEN_PATH, graph_error(190, "Expired"), 400)
    with pytest.raises(ValidationFailedError):
        refresh(graph)

    assert len(graph.requests) == 2
    assert_nothing_secret(process_log.getvalue())


def guarded(
    graph: RecordingTransport,
) -> tuple[CircuitBreakingMetaTokenRefreshAdapter, CircuitBreakerFacilitator]:
    breaker = CircuitBreakerFacilitator(Ticks().clock())
    adapter = CircuitBreakingMetaTokenRefreshAdapter(
        inner_client=MetaOAuthClient(transport=graph.build()),
        circuit_breaker=breaker,
        circuit=META,
    )
    return adapter, breaker


def test_an_open_circuit_refuses_without_asking_meta() -> None:
    graph = RecordingTransport()
    graph.respond("GET", TOKEN_PATH, {"access_token": "EAAfake-token-2"})
    adapter, breaker = guarded(graph)

    assert adapter.refresh_business_token(TOKEN, APP) == "EAAfake-token-2"
    for _ in range(5):
        breaker.record_failure(META)

    with pytest.raises(ProviderCircuitOpenError):
        adapter.refresh_business_token(TOKEN, APP)
    assert len(graph.requests) == 1


def test_timeouts_count_against_the_circuit() -> None:
    graph = RecordingTransport(failure=httpx.ReadTimeout("timed out"))
    adapter, breaker = guarded(graph)

    for _ in range(5):
        with pytest.raises(ExternalServiceError):
            adapter.refresh_business_token(TOKEN, APP)

    assert breaker.state(META) is CircuitState.OPEN
    with pytest.raises(ProviderCircuitOpenError):
        adapter.refresh_business_token(TOKEN, APP)
    assert len(graph.requests) == 5


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (400, graph_error(190, "Error validating access token.")),
        (401, {}),
        (429, {}),
    ],
    ids=["refused", "rejected", "slow-down"],
)
def test_meta_s_refusals_leave_the_circuit_closed(
    status: int, body: dict[str, object]
) -> None:
    adapter, breaker = guarded(answering(status, body))

    for _ in range(6):
        with pytest.raises(ApplicationError):
            adapter.refresh_business_token(TOKEN, APP)

    assert breaker.state(META) is CircuitState.CLOSED
