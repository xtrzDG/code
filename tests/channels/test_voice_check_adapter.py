"""
The voice checks at ElevenLabs agent testing: an agent nobody can call,
one run per language with the agent answering in it, polls until the
runs finish or the time is up, and nothing left behind.
"""

import pytest

from app.schemas.constants.voice_checks import VoiceCheckStatus
from app.schemas.exceptions.application_errors import ExternalServiceError
from tests.channels.voice_check_setup import (
    POLL_SECONDS,
    WAIT_SECONDS,
    batch,
    build_voice_check_setup,
    finished_invocation,
    pending_invocation,
)


def test_each_language_runs_with_the_agent_answering_in_it() -> None:
    setup = build_voice_check_setup()
    setup.transport.respond_in_turn(
        "POST",
        r"^/v1/convai/agent-testing/create$",
        [(200, {"id": "test_ka"}), (200, {"id": "test_ru"})],
    )
    setup.transport.respond_in_turn(
        "POST",
        r"/run-tests$",
        [
            (200, {"id": "suite_ka", "test_runs": []}),
            (200, {"id": "suite_ru", "test_runs": []}),
        ],
    )
    setup.transport.respond(
        "GET", r"/test-invocations/suite_ka$", finished_invocation("test_ka")
    )
    setup.transport.respond(
        "GET",
        r"/test-invocations/suite_ru$",
        finished_invocation("test_ru", status="failed"),
    )

    outcomes = setup.adapter.run_checks(batch("ka", "ru"))

    assert [(str(outcome.key), outcome.status) for outcome in outcomes] == [
        ("phone__booking__ka", VoiceCheckStatus.PASSED),
        ("phone__booking__ru", VoiceCheckStatus.FAILED),
    ]
    runs = setup.transport.requests_to("/run-tests")
    assert [request.json()["tests"] for request in runs] == [
        [{"test_id": "test_ka"}],
        [{"test_id": "test_ru"}],
    ]
    overrides = [request.json()["agent_config_override"] for request in runs]
    assert [
        override["conversation_config"]["agent"]["language"] for override in overrides
    ] == ["ka", "ru"]
    assert [
        override["conversation_config"]["agent"]["first_message"]
        for override in overrides
    ] == ["Greeting ka", "Greeting ru"]
    assert all(str(run.url.path).endswith("/agent_check/run-tests") for run in runs)


def test_the_agent_of_the_checks_cannot_take_a_real_call_or_run_a_tool() -> None:
    setup = build_voice_check_setup()
    setup.transport.respond(
        "POST", r"^/v1/convai/agent-testing/create$", {"id": "test_ka"}
    )
    setup.transport.respond("POST", r"/run-tests$", {"id": "suite_ka"})
    setup.transport.respond(
        "GET", r"/test-invocations/suite_ka$", finished_invocation("test_ka")
    )

    setup.adapter.run_checks(batch("ka"))

    [agent] = setup.transport.requests_to("/agents/create")
    body = agent.json()
    assert "voice-check" in body["tags"]
    # No call-initiation webhook: no number or widget reaches it.
    assert "workspace_overrides" not in body["platform_settings"]
    for tool in setup.transport.requests_to("/convai/tools"):
        if tool.method != "POST":
            continue
        headers = tool.json()["tool_config"]["api_schema"]["request_headers"]
        # The business id but no tool secret: the tool endpoints refuse.
        assert set(headers) == {"X-Assistant-Business-Id"}
    [test] = setup.transport.requests_to("/agent-testing/create")
    mocks = test.json()
    assert mocks["tool_mock_config"] == {
        "mocking_strategy": "all",
        "fallback_strategy": "raise_error",
    }
    assert mocks["dynamic_variables"]["local_now"] == "Thursday 2026-10-01 14:05"


def test_runs_are_polled_until_they_finish_and_everything_is_deleted() -> None:
    setup = build_voice_check_setup()
    setup.transport.respond(
        "POST", r"^/v1/convai/agent-testing/create$", {"id": "test_ka"}
    )
    setup.transport.respond("POST", r"/run-tests$", {"id": "suite_ka"})
    setup.transport.respond_in_turn(
        "GET",
        r"/test-invocations/suite_ka$",
        [
            (200, pending_invocation("test_ka")),
            (503, {"detail": "busy"}),
            (200, finished_invocation("test_ka")),
        ],
    )

    [outcome] = setup.adapter.run_checks(batch("ka"))

    assert outcome.status is VoiceCheckStatus.PASSED
    assert setup.sleeps == [POLL_SECONDS] * 3
    deleted = [
        request.path
        for request in setup.transport.requests
        if request.method == "DELETE"
    ]
    assert deleted == [
        "/v1/convai/agent-testing/test_ka",
        "/v1/convai/agents/agent_check",
        "/v1/convai/tools/tool_check",
        "/v1/convai/tools/tool_check",
    ]


def test_a_run_still_going_when_the_time_is_up_is_unfinished() -> None:
    setup = build_voice_check_setup()
    setup.transport.respond(
        "POST", r"^/v1/convai/agent-testing/create$", {"id": "test_ka"}
    )
    setup.transport.respond("POST", r"/run-tests$", {"id": "suite_ka"})
    setup.transport.respond(
        "GET", r"/test-invocations/suite_ka$", pending_invocation("test_ka")
    )

    [outcome] = setup.adapter.run_checks(batch("ka"))

    assert outcome.status is VoiceCheckStatus.UNFINISHED
    assert sum(setup.sleeps) == WAIT_SECONDS
    assert setup.transport.requests_to("/agents/agent_check")[-1].method == "DELETE"


def test_a_language_the_platform_refuses_errs_alone() -> None:
    setup = build_voice_check_setup()
    setup.transport.respond_in_turn(
        "POST",
        r"^/v1/convai/agent-testing/create$",
        [(200, {"id": "test_ka"}), (422, {"detail": "bad test"})],
    )
    setup.transport.respond("POST", r"/run-tests$", {"id": "suite_ka"})
    setup.transport.respond(
        "GET", r"/test-invocations/suite_ka$", finished_invocation("test_ka")
    )

    outcomes = setup.adapter.run_checks(batch("ka", "ru"))

    assert [outcome.status for outcome in outcomes] == [
        VoiceCheckStatus.PASSED,
        VoiceCheckStatus.ERRORED,
    ]


def test_an_agent_that_cannot_be_set_up_fails_the_batch_and_leaves_no_tool() -> None:
    setup = build_voice_check_setup()
    setup.transport.respond(
        "POST", r"^/v1/convai/agents/create$", {"detail": "quota"}, status_code=402
    )

    with pytest.raises(ExternalServiceError):
        setup.adapter.run_checks(batch("ka"))

    assert setup.transport.requests_to("/agent-testing") == []
    assert [
        request.path
        for request in setup.transport.requests
        if request.method == "DELETE"
    ] == ["/v1/convai/tools/tool_check", "/v1/convai/tools/tool_check"]


def test_no_cases_ask_nothing() -> None:
    setup = build_voice_check_setup()

    assert setup.adapter.run_checks(batch()) == []
    assert setup.transport.requests == []
