"""
The voice checks end to end over the real container: assembling the
Georgian restaurant's version with voice queues its autotests, the worker
plays a simulated call per language at ElevenLabs agent testing (with the
agent answering in that language), the run lists them with the channel
PHONE, nothing is left at ElevenLabs, and the version goes live.
"""

from app.adapters.voice.elevenlabs_voice_check_adapter import (
    ElevenLabsVoiceCheckAdapter,
)
from app.clients.elevenlabs.elevenlabs_client import ElevenLabsClient
from app.containers.app import AppContainer
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.strings import PlatformSecret
from tests.e2e.edge_fakes import RecordedHttp, build_transport
from tests.e2e.harness import bearer, start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT, ELEVENLABS_BASE_URL
from tests.e2e.journeys import open_restaurant
from tests.e2e.voice_check_fakes import SimulatedCalls
from tests.e2e.workshop_container import replace_provider


def test_a_voice_version_goes_live_after_its_simulated_calls_passed() -> None:
    calls = SimulatedCalls()
    elevenlabs = RecordedHttp()

    def prepare(container: AppContainer) -> None:
        replace_provider(
            container.clients.elevenlabs_client,
            ElevenLabsClient(
                api_key=PlatformSecret("xi-e2e-key"),
                base_url=PublicBaseUrl(ELEVENLABS_BASE_URL),
                transport=build_transport(elevenlabs, calls),
            ),
        )
        # The real adapter over the guarded client; a poll does not sleep.
        replace_provider(
            container.adapters.voice_check_adapter,
            ElevenLabsVoiceCheckAdapter(
                container.adapters.counted_elevenlabs_client(),
                container.config.app_settings(),
                container.time_provider.monotonic_clock(),
                sleep=lambda seconds: None,
            ),
        )

    workshop = start_workshop(
        {**E2E_ENVIRONMENT, "VOICE_CHECKS_ENABLED": "true"}, prepare
    )
    with workshop.client:
        restaurant = open_restaurant(workshop)
        run = workshop.client.get(
            f"/v1/businesses/{restaurant.business_id}/assistant-versions/"
            f"{restaurant.version_id}/autotest-run",
            headers=bearer(restaurant.owner_token),
        )

    assert run.status_code == 200, run.text
    phone = [result for result in run.json()["results"] if result["channel"] == "phone"]
    assert [(result["language"], result["outcome"]) for result in phone] == [
        ("ka", "passed"),
        ("ru", "passed"),
        ("en", "passed"),
    ]
    started = elevenlabs.bodies("/run-tests")
    assert [
        body["agent_config_override"]["conversation_config"]["agent"]["language"]
        for body in started
    ] == ["ka", "ru", "en"]
    deleted = [
        request.url.path
        for request in elevenlabs.requests
        if request.method == "DELETE"
    ]
    assert sorted(path for path in deleted if "/agent-testing/" in path) == sorted(
        f"/v1/convai/agent-testing/{test_id}" for test_id in calls.tests
    )
    assert "/v1/convai/agents/agent_e2e" in deleted
