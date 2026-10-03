"""End-to-end harness: the real AppContainer with overrides only at the edges.

- settings come from `assemble_app_settings` with an explicit mapping;
- "now" is a movable wall clock;
- the language model is a ScriptedLlmAdapter that plays the assistant, the
  autotest customer and the judge;
- sign-in codes are captured instead of sent;
- every external HTTP client talks to an httpx.MockTransport that records
  the requests (Telegram, Meta, ElevenLabs, Google), and the OpenAI and
  Anthropic SDK factories fail the test if they are ever used.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.containers.app import AppContainer
from app.gateways.worker.background_worker import WorkerTickReport
from app.main import build_application
from tests.e2e.edge_fakes import CapturingOtpDelivery, MovableClock, RecordedHttp
from tests.e2e.harness_settings import E2E_ENVIRONMENT, START, JsonObject
from tests.e2e.workshop_container import build_workshop_container
from tests.e2e.workshop_model_script import WorkshopModelScript


@dataclass
class Workshop:
    """A running API over the real container, plus its fakes."""

    container: AppContainer
    application: FastAPI
    client: TestClient
    clock: MovableClock
    otp: CapturingOtpDelivery
    model: WorkshopModelScript
    llm: ScriptedLlmAdapter
    telegram: RecordedHttp
    meta: RecordedHttp
    elevenlabs: RecordedHttp
    google: RecordedHttp
    langfuse: RecordedHttp

    def run_queued_jobs(self) -> WorkerTickReport:
        """
        What the background worker does with the queue right now: answer
        the inbox, send the outbox (webhooks only store their messages).
        """

        return self.container.gateways.background_worker().run_queued_jobs()

    def sign_in_with_phone(self, raw_phone: str) -> tuple[str, JsonObject]:
        started = self.client.post(
            "/v1/auth/otp/start", json={"phone_number": raw_phone}
        )
        assert started.status_code == 200, started.text
        return self._verify(started.json())

    def sign_in_with_email(self, email: str) -> tuple[str, JsonObject]:
        started = self.client.post("/v1/auth/otp/start", json={"email": email})
        assert started.status_code == 200, started.text
        return self._verify(started.json())

    def _verify(self, challenge: JsonObject) -> tuple[str, JsonObject]:
        verified = self.client.post(
            "/v1/auth/otp/verify",
            json={
                "challenge_id": challenge["challenge_id"],
                "code": str(self.otp.codes[-1].code),
            },
        )
        assert verified.status_code == 200, verified.text
        session: JsonObject = verified.json()
        return str(session["access_token"]), session


def bearer(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def start_workshop(
    environment: Mapping[str, str] | None = None,
    prepare: Callable[[AppContainer], None] | None = None,
) -> Workshop:
    """
    Build the container and the API; the caller enters `client`. `prepare`
    may override more providers before the API is built.
    """

    clock = MovableClock(START)
    otp = CapturingOtpDelivery()
    model = WorkshopModelScript()
    llm = ScriptedLlmAdapter(model)
    telegram, meta, elevenlabs, google, langfuse = (
        RecordedHttp(),
        RecordedHttp(),
        RecordedHttp(),
        RecordedHttp(),
        RecordedHttp(),
    )
    container = build_workshop_container(
        E2E_ENVIRONMENT if environment is None else environment,
        clock,
        otp,
        llm,
        telegram,
        meta,
        elevenlabs,
        google,
        langfuse,
    )
    if prepare is not None:
        prepare(container)

    application = build_application(container)
    return Workshop(
        container=container,
        application=application,
        client=TestClient(application),
        clock=clock,
        otp=otp,
        model=model,
        llm=llm,
        telegram=telegram,
        meta=meta,
        elevenlabs=elevenlabs,
        google=google,
        langfuse=langfuse,
    )
