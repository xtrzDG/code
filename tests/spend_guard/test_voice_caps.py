"""
Voice brakes: every agent carries the call caps (CALL_MAX_DURATION_SECONDS,
CALL_SILENCE_END_SECONDS), and past its hard spend limit a business takes
no calls on the voice agent.
"""

from typing import Any

import pytest

from app.adapters.voice.elevenlabs_voice_agent_provisioner import (
    ElevenLabsVoiceAgentProvisioner,
)
from app.registries.billing.plan_registry import PlanRegistry
from app.schemas.constants.spend import SpendLevel
from app.schemas.dto.voice_webhooks import (
    CallInitiationWebhookRequest,
    VoiceWebhookCredentials,
)
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.channels.strings import PresentedWebhookSecret
from app.use_cases.voice.start_voice_call_use_case import StartVoiceCallUseCase
from tests.channels.channels_payloads import to_json_bytes
from tests.channels.channels_settings import build_settings
from tests.channels.testbed import ChannelsTestbed
from tests.channels.voice_agent_specs import build_spec
from tests.channels.voice_setup import (
    ASSISTANT_LINE,
    CALLER,
    VoiceSetup,
    build_voice_setup,
    tool_secret,
)
from tests.spend_guard.test_spend_turns import FixedSpendCheck


def created_agent(testbed: ChannelsTestbed, **settings: str) -> dict[str, Any]:
    transport = testbed.elevenlabs_transport
    transport.respond("POST", r"^/v1/convai/tools$", {"id": "tool_new"})
    transport.respond("POST", r"^/v1/convai/agents/create$", {"agent_id": "agent_1"})
    ElevenLabsVoiceAgentProvisioner(
        testbed.elevenlabs_client, build_settings(**settings)
    ).upsert_agent(build_spec())
    agent: dict[str, Any] = transport.requests_to("/agents/create")[0].json()
    config: dict[str, Any] = agent["conversation_config"]
    return config


def test_the_default_call_caps_reach_the_agent_config() -> None:
    config = created_agent(ChannelsTestbed())

    assert config["conversation"] == {"max_duration_seconds": 600}
    assert config["turn"] == {"silence_end_call_timeout": 30}


def test_the_configured_call_caps_reach_the_agent_config() -> None:
    config = created_agent(
        ChannelsTestbed(),
        CALL_MAX_DURATION_SECONDS="300",
        CALL_SILENCE_END_SECONDS="15",
    )

    assert config["conversation"]["max_duration_seconds"] == 300
    assert config["turn"]["silence_end_call_timeout"] == 15


def start_call(setup: VoiceSetup, level: SpendLevel) -> FixedSpendCheck:
    testbed = setup.testbed
    spend = FixedSpendCheck(level)
    StartVoiceCallUseCase(
        testbed.business_repo,
        testbed.assistant_version_repo,
        testbed.channel_repo,
        PlanRegistry(),
        testbed.profile_repo,
        testbed.exception_repo,
        testbed.contact_repo,
        testbed.booking_repo,
        testbed.resource_repo,
        testbed.wall_clock,
        testbed.voice_webhook_adapter,
        testbed.phone_number_parser,
        testbed.call_greeting,
        testbed.settings,
        check_spend=spend,
    ).run(
        CallInitiationWebhookRequest(
            credentials=VoiceWebhookCredentials(
                business_id=setup.business.id,
                tool_secret=PresentedWebhookSecret(tool_secret(setup.business.id)),
            ),
            body=to_json_bytes(
                {
                    "caller_id": CALLER,
                    "agent_id": "agent_1",
                    "called_number": ASSISTANT_LINE,
                }
            ),
        )
    )
    return spend


def test_calls_are_answered_under_the_hard_limit() -> None:
    setup = build_voice_setup()

    spend = start_call(setup, SpendLevel.SOFT_LIMIT)

    (request,) = spend.requests
    assert request.model_id is None


def test_past_the_hard_limit_the_voice_agent_takes_no_calls() -> None:
    setup = build_voice_setup()

    with pytest.raises(ConflictError, match="daily spend limit"):
        start_call(setup, SpendLevel.HARD_LIMIT)
