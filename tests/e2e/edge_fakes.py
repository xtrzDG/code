"""The workshop's edges, faked so that nothing leaves the test.

Sign-in codes are captured, the clock moves only when told to, HTTP traffic
(Telegram, Meta, ElevenLabs, Google, Langfuse) is recorded and answered, and
the OpenAI and Anthropic SDK factories fail the test if they are ever used.
"""

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import cast

import anthropic
import httpx
import openai
from typed_time_provider import Microseconds, WallClock

from app.contracts.facilitators import OtpDeliveryFacilitatorContract
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.users.constrained_strings import EmailAddress, OtpCode
from tests.e2e.harness_settings import JsonObject


@dataclass(frozen=True)
class CapturedCode:
    channel: OtpDeliveryChannel
    phone_number: E164PhoneNumber | None
    email: EmailAddress | None
    code: OtpCode
    language: LanguageTag


class CapturingOtpDelivery(OtpDeliveryFacilitatorContract):
    """Keeps every sign-in code so the test can type it back."""

    def __init__(self) -> None:
        self.codes: list[CapturedCode] = []

    def available_channels(self) -> frozenset[OtpDeliveryChannel]:
        return frozenset(OtpDeliveryChannel)

    def deliver(
        self,
        delivery_channel: OtpDeliveryChannel,
        phone_number: E164PhoneNumber | None,
        email: EmailAddress | None,
        code: OtpCode,
        language_tag: LanguageTag,
    ) -> None:
        self.codes.append(
            CapturedCode(delivery_channel, phone_number, email, code, language_tag)
        )


class MovableClock:
    """Wall clock (microseconds) that tests move forward."""

    def __init__(self, moment: datetime) -> None:
        self._nanoseconds: int = to_nanoseconds(moment)
        self.wall_clock: WallClock[Microseconds] = WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: self._nanoseconds,
        )

    def advance(self, seconds: int) -> None:
        self._nanoseconds += seconds * 1_000_000_000


def to_nanoseconds(moment: datetime) -> int:
    delta = moment.astimezone(UTC) - datetime(1970, 1, 1, tzinfo=UTC)
    return (delta.days * 86_400 + delta.seconds) * 1_000_000_000


@dataclass
class RecordedHttp:
    """Requests that reached one fake external service."""

    requests: list[httpx.Request] = field(default_factory=list[httpx.Request])

    def paths(self) -> list[str]:
        return [request.url.path for request in self.requests]

    def bodies(self, path_suffix: str) -> list[JsonObject]:
        return [
            cast(JsonObject, json.loads(request.content))
            for request in self.requests
            if request.url.path.endswith(path_suffix)
        ]


def build_transport(
    recorded: RecordedHttp,
    respond: Callable[[httpx.Request], JsonObject],
) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        recorded.requests.append(request)
        return httpx.Response(200, json=respond(request))

    return httpx.MockTransport(handle)


def answer_telegram(request: httpx.Request) -> JsonObject:
    method: str = request.url.path.rsplit("/", 1)[-1]
    if method == "getMe":
        return {"ok": True, "result": {"id": 42, "username": "workshop_bot"}}

    if method == "sendMessage":
        return {"ok": True, "result": {"message_id": 1}}

    return {"ok": True, "result": True}


def answer_elevenlabs(request: httpx.Request) -> JsonObject:
    path: str = request.url.path
    if request.method == "POST" and path == "/v1/convai/tools":
        return {"id": f"tool_{hashlib.sha256(request.content).hexdigest()[:12]}"}

    if request.method == "POST" and path == "/v1/convai/agents/create":
        return {"agent_id": "agent_e2e"}

    return {}


def answer_with_empty_object(request: httpx.Request) -> JsonObject:
    del request
    return {}


def refuse_openai_sdk() -> openai.OpenAI:
    raise AssertionError("The OpenAI API must not be called in end-to-end tests.")


def refuse_anthropic_sdk() -> anthropic.Anthropic:
    raise AssertionError("The Anthropic API must not be called in end-to-end tests.")
