"""Failover: a failing provider's call is rerun on the other provider's model."""

import pytest

from app.schemas.constants.resilience import CircuitState
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    LlmRefusedError,
)
from app.schemas.typings.resilience.constrained_strings import CircuitName
from tests.resilience.failover_fakes import (
    FALLBACK_MODEL,
    PRIMARY_MODEL,
    answering,
    build_request,
    failing,
    real_breaker,
    refusing,
    router,
    timed,
)

OPENAI_CIRCUIT: CircuitName = CircuitName("openai:gpt-5-mini")
ANTHROPIC_CIRCUIT: CircuitName = CircuitName("anthropic:claude-sonnet-5-5")
VERBATIM: list[str] = [
    '{"role": "user", "content": [{"type": "text", "text": "Hi"}]}',
    '{"role": "assistant", "provider": "openai", "items": [{"type": "reasoning"}]}',
]
CANONICAL: list[str] = [
    '{"role": "user", "content": [{"type": "text", "text": "Hi"}]}',
    '{"role": "assistant", "content": [{"type": "text", "text": "Hello!"}]}',
]


def test_a_failed_call_is_rerun_on_the_fallback_with_the_canonical_transcript() -> (
    None
):
    openai = failing()
    anthropic = answering("from anthropic")

    response = router(openai, anthropic).complete(
        build_request(transcript=VERBATIM, fallback_transcript=CANONICAL)
    )

    assert response.text == "from anthropic"
    assert response.fallback_model_id == FALLBACK_MODEL
    [rerun] = anthropic.requests
    assert rerun.model_id == FALLBACK_MODEL
    assert [str(turn) for turn in rerun.transcript] == CANONICAL
    assert rerun.fallback_transcript is None
    # The version's own provider got the verbatim transcript first.
    assert [str(turn) for turn in openai.requests[0].transcript] == VERBATIM


def test_a_working_provider_answers_without_the_fallback() -> None:
    anthropic = answering("from anthropic")

    response = router(answering("from openai"), anthropic).complete(build_request())

    assert response.text == "from openai"
    assert response.fallback_model_id is None
    assert anthropic.requests == []


def test_a_refusal_is_the_models_answer_and_is_not_rerun() -> None:
    anthropic = answering("from anthropic")
    breaker = real_breaker()

    with pytest.raises(LlmRefusedError):
        router(refusing(), anthropic, breaker).complete(build_request())

    assert anthropic.requests == []
    assert breaker.state(OPENAI_CIRCUIT) is CircuitState.CLOSED


def test_an_open_breaker_answers_within_a_second_through_the_fallback() -> None:
    breaker = real_breaker()
    # The provider hangs for 3 s before it fails, as a slow outage does.
    openai = failing(seconds=3.0)
    for _ in range(5):
        breaker.record_failure(OPENAI_CIRCUIT)

    response, seconds = timed(
        lambda: router(openai, answering("from anthropic"), breaker).complete(
            build_request()
        )
    )

    assert response.text == "from anthropic"
    assert response.fallback_model_id == FALLBACK_MODEL
    assert seconds < 1.0
    assert openai.requests == []


def test_five_failures_open_the_circuit_and_later_calls_skip_the_provider() -> None:
    breaker = real_breaker()
    openai = failing()
    routed = router(openai, answering("from anthropic"), breaker)

    for _ in range(6):
        assert routed.complete(build_request()).text == "from anthropic"

    assert len(openai.requests) == 5
    assert breaker.state(OPENAI_CIRCUIT) is CircuitState.OPEN
    assert breaker.state(ANTHROPIC_CIRCUIT) is CircuitState.CLOSED


def test_the_original_failure_is_raised_when_the_fallback_fails_too() -> None:
    with pytest.raises(ExternalServiceError, match="server_error"):
        router(failing(), failing()).complete(build_request())


def test_an_open_fallback_circuit_is_not_tried() -> None:
    breaker = real_breaker()
    anthropic = answering("from anthropic")
    for _ in range(5):
        breaker.record_failure(ANTHROPIC_CIRCUIT)

    with pytest.raises(ExternalServiceError, match="server_error"):
        router(failing(), anthropic, breaker).complete(build_request())

    assert anthropic.requests == []


def test_both_circuits_open_is_reported_as_unavailable() -> None:
    breaker = real_breaker()
    for _ in range(5):
        breaker.record_failure(OPENAI_CIRCUIT)
        breaker.record_failure(ANTHROPIC_CIRCUIT)

    with pytest.raises(ExternalServiceError, match="both unavailable"):
        router(failing(), answering("x"), breaker).complete(build_request())


@pytest.mark.parametrize("fallback", [None, PRIMARY_MODEL])
def test_without_a_usable_fallback_errors_are_raised_as_they_are(
    fallback: object,
) -> None:
    anthropic = answering("from anthropic")
    routed = router(
        failing(),
        anthropic,
        fallback_model_id=None if fallback is None else PRIMARY_MODEL,
    )

    with pytest.raises(ExternalServiceError):
        routed.complete(build_request())

    assert anthropic.requests == []


def test_a_fallback_of_an_unknown_provider_is_ignored() -> None:
    from app.schemas.typings.assistants.constrained_strings import LlmModelId

    routed = router(failing(), answering("x"), fallback_model_id=LlmModelId("mistral"))

    with pytest.raises(ExternalServiceError):
        routed.complete(build_request())


def test_without_a_breaker_a_failure_still_fails_over() -> None:
    from app.adapters.llm.routing_llm_adapter import RoutingLlmAdapter

    routed = RoutingLlmAdapter(
        failing(), answering("from anthropic"), fallback_model_id=FALLBACK_MODEL
    )

    assert routed.complete(build_request()).text == "from anthropic"


def test_the_fallback_reuses_the_transcript_when_none_was_given() -> None:
    anthropic = answering("from anthropic")

    router(failing(), anthropic).complete(build_request(transcript=CANONICAL))

    assert [str(turn) for turn in anthropic.requests[0].transcript] == CANONICAL
