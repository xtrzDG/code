"""
End-to-end harness: the real AppContainer with overrides only at the edges.

- settings come from `assemble_app_settings` with an explicit mapping;
- "now" is a movable wall clock;
- the language model is a ScriptedLlmAdapter that plays the assistant, the
  autotest customer and the judge;
- sign-in codes are captured instead of sent;
- every external HTTP client talks to an httpx.MockTransport that records
  the requests (Telegram, Meta, ElevenLabs, Google), and the OpenAI and
  Anthropic SDK factories fail the test if they are ever used.
"""

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol, cast

import anthropic
import httpx
import openai
from dependency_injector import providers
from fastapi import FastAPI
from fastapi.testclient import TestClient
from typed_time_provider import Microseconds, WallClock

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.clients.anthropic.anthropic_messages_client import AnthropicMessagesClient
from app.clients.elevenlabs.elevenlabs_client import ElevenLabsClient
from app.clients.google.google_calendar_client import GoogleCalendarClient
from app.clients.langfuse.langfuse_ingestion_client import LangfuseIngestionClient
from app.clients.meta.meta_graph_client import MetaGraphClient
from app.clients.openai.openai_responses_client import OpenAiResponsesClient
from app.clients.telegram.telegram_bot_client import TelegramBotClient
from app.containers.app import AppContainer
from app.contracts.facilitators import OtpDeliveryFacilitatorContract
from app.main import build_application
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.dto.conversations import LlmRequest
from app.schemas.dto.llm_scripts import ScriptedLlmTurn, ScriptedToolCall
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.conversations.strings import LlmToolInputJson, MessageText
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.users.constrained_strings import EmailAddress, OtpCode
from app.utilities.assembly.autotest_prompts import DONE_MARKER, JUDGE_SYSTEM_PROMPT
from app.utilities.config_helpers.app_settings_assembler import assemble_app_settings

# Monday 2026-10-05 08:00 UTC: 12:00 in Tbilisi, 10:00 in Rome.
START: datetime = datetime(2026, 10, 5, 8, 0, tzinfo=UTC)
API_BASE_URL: str = "https://api.workshop.example"
CABINET_ORIGIN: str = "https://cabinet.workshop.example"
ADMIN_EMAIL: str = "admin@workshop.example"
PLATFORM_BOT_TOKEN: str = "123456:platform-bot-token"
ELEVENLABS_BASE_URL: str = "https://elevenlabs.test"
E2E_ENVIRONMENT: dict[str, str] = {
    "APP_ENV": "test",
    "APP_BASE_URL": API_BASE_URL,
    "CORS_ALLOWED_ORIGINS": CABINET_ORIGIN,
    "ENCRYPTION_KEY": "e2e-encryption-secret-0123456789abcdef",
    "LLM_PROVIDER": "scripted",
    "PLATFORM_ADMIN_EMAILS": ADMIN_EMAIL,
    "TELEGRAM_PLATFORM_BOT_TOKEN": PLATFORM_BOT_TOKEN,
    "ELEVENLABS_API_KEY": "xi-e2e-key",
    "ELEVENLABS_WEBHOOK_SECRET": "elevenlabs-webhook-secret-e2e",
}

type JsonObject = dict[str, Any]


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


def call_tool(tool_name: AssistantToolName, arguments: JsonObject) -> ScriptedLlmTurn:
    return ScriptedLlmTurn(
        tool_calls=[
            ScriptedToolCall(
                tool_name=tool_name,
                input_json=LlmToolInputJson(json.dumps(arguments, ensure_ascii=False)),
            )
        ]
    )


def say(text: str) -> ScriptedLlmTurn:
    return ScriptedLlmTurn(text=MessageText(text))


def read_turn(payload: str) -> JsonObject:
    return cast(JsonObject, json.loads(payload))


def read_turn_texts(payload: str) -> str:
    content: list[JsonObject] = read_turn(payload)["content"]
    return "\n".join(str(block.get("text", "")) for block in content)


def last_tool_call(request: LlmRequest) -> tuple[str, JsonObject] | None:
    """Name and parsed result of the tool answered in the last turn, if any."""

    last_turn: JsonObject = read_turn(request.transcript[-1])
    results: list[JsonObject] = [
        block for block in last_turn["content"] if block.get("type") == "tool_result"
    ]
    if not results:
        return None

    assistant_turn: JsonObject = read_turn(request.transcript[-2])
    calls: list[JsonObject] = [
        block for block in assistant_turn["content"] if block.get("type") == "tool_use"
    ]
    return str(calls[-1]["name"]), cast(JsonObject, json.loads(results[-1]["content"]))


LANGUAGE_TAG_PATTERN: re.Pattern[str] = re.compile(r"language tag ([A-Za-z\-]+)\)")
GOAL_PATTERN: re.Pattern[str] = re.compile(r"^Your goal: (.+)$", re.MULTILINE)
# What the AI customer writes, by scenario language and intent.
CUSTOMER_MESSAGES: dict[str, dict[str, str]] = {
    "ka": {
        "booking": "მინდა მაგიდის დაჯავშნა",
        "price": "რა ღირს ხაჭაპური?",
        "human": "მენეჯერთან დამაკავშირეთ, გთხოვთ",
        "other": "გამარჯობა, კითხვა მაქვს",
    },
    "ru": {
        "booking": "Хочу забронировать столик",
        "price": "Сколько стоит хачапури?",
        "human": "Позовите менеджера, пожалуйста",
        "other": "Здравствуйте, у меня вопрос",
    },
    "en": {
        "booking": "I would like to book a table",
        "price": "How much is khachapuri?",
        "human": "Let me talk to a manager, please",
        "other": "Hello, I have a question",
    },
}
# What the assistant answers, in the language the customer wrote in.
ASSISTANT_TEXTS: dict[str, dict[str, str]] = {
    "ka": {
        "greeting": "გამარჯობა! რით შემიძლია დაგეხმაროთ?",
        "booked": "მზადაა! მაგიდა დაჯავშნილია 19:00-ზე.",
        "price": "ხაჭაპურის ფასია {price}.",
        "no_price": "სამწუხაროდ, ფასი ვერ ვიპოვე.",
        "fine": "კარგი.",
    },
    "ru": {
        "greeting": "Здравствуйте! Чем могу помочь?",
        "booked": "Готово, Нино! Ваш столик забронирован на 19:00.",
        "price": "Хачапури стоит {price}.",
        "no_price": "К сожалению, цену не нашёл.",
        "fine": "Хорошо.",
    },
    "en": {
        "greeting": "Hello! How can I help?",
        "booked": "Done! Your table is booked for 19:00.",
        "price": "Khachapuri costs {price}.",
        "no_price": "Sorry, I could not find the price.",
        "fine": "All right.",
    },
}
HANDOFF_WORDS: tuple[str, ...] = ("менеджер", "მენეჯერ", "manager")
BOOKING_WORDS: tuple[str, ...] = ("забронировать", "დაჯავშნა", "book a table")
PRICE_WORDS: tuple[str, ...] = ("ღირს", "Сколько стоит", "How much")


def read_customer_intent(goal: str) -> str:
    """The AI customer's intent from the scenario goal of its instruction."""

    if goal.startswith("Book a "):
        return "booking"

    if goal.startswith("Ask how much"):
        return "price"

    if goal.startswith(("Ask to talk to a human", "Report an emergency")):
        return "human"

    return "other"


def detect_language(text: str) -> str:
    """ka, ru or en by the script the customer wrote in."""

    if any("\u10a0" <= character <= "\u10ff" for character in text):
        return "ka"

    if any("\u0400" <= character <= "\u04ff" for character in text):
        return "ru"

    return "en"


def last_customer_text(request: LlmRequest) -> str:
    """Text of the latest turn the customer wrote (not a tool result)."""

    for payload in reversed(request.transcript):
        turn: JsonObject = read_turn(payload)
        if turn["role"] != "user":
            continue

        texts: list[str] = [
            str(block["text"])
            for block in turn["content"]
            if block.get("type") == "text"
        ]
        if texts:
            return "\n".join(texts)

    return ""


class WorkshopModelScript:
    """
    The scripted language model of the journey. It plays three roles, told
    apart by the request: the judge (judge prompt), the autotest customer
    (no tools) and the assistant (tools offered). The customer writes one
    message for its scenario goal in the scenario language; the assistant
    answers in the language the customer wrote in, books, quotes prices
    through get_price and hands off when asked for a manager.
    """

    def __init__(self) -> None:
        self.assistant_calls: int = 0
        self.customer_calls: int = 0
        self.judge_calls: int = 0
        self.tool_calls: list[str] = []
        self.booking_request: JsonObject = {}

    def __call__(self, request: LlmRequest) -> ScriptedLlmTurn:
        if str(request.system_prompt) == JUDGE_SYSTEM_PROMPT:
            self.judge_calls += 1
            return say(
                json.dumps(
                    {
                        "scores": {
                            "facts_and_prices": 5,
                            "booking_data": 5,
                            "ai_disclosure": 5,
                            "handoff": 5,
                            "language": 5,
                        },
                        "notes": [],
                    }
                )
            )

        if not request.tools:
            self.customer_calls += 1
            return self._play_customer(request)

        self.assistant_calls += 1
        language: str = detect_language(last_customer_text(request))
        answered: tuple[str, JsonObject] | None = last_tool_call(request)
        if answered is not None:
            return self._after_tool(*answered, language=language)

        return self._answer(read_turn_texts(request.transcript[-1]), language)

    def _play_customer(self, request: LlmRequest) -> ScriptedLlmTurn:
        customer_turns: int = sum(
            1 for payload in request.transcript if read_turn(payload)["role"] == "user"
        )
        if customer_turns > 1:
            return say(DONE_MARKER)

        prompt: str = str(request.system_prompt)
        language_match: re.Match[str] | None = LANGUAGE_TAG_PATTERN.search(prompt)
        goal_match: re.Match[str] | None = GOAL_PATTERN.search(prompt)
        assert language_match is not None and goal_match is not None, prompt
        return say(
            CUSTOMER_MESSAGES[language_match.group(1)][
                read_customer_intent(goal_match.group(1))
            ]
        )

    def _answer(self, customer_text: str, language: str) -> ScriptedLlmTurn:
        if any(word in customer_text for word in HANDOFF_WORDS):
            return self._call(
                AssistantToolName.HANDOFF_TO_HUMAN,
                {
                    "reason": "customer_request",
                    "summary": "The customer asks for a manager.",
                    "urgency": "normal",
                },
            )

        if any(word in customer_text for word in BOOKING_WORDS):
            return self._call(
                AssistantToolName.CHECK_AVAILABILITY,
                {
                    "resource_type": None,
                    "date": "2026-10-06",
                    "time": "19:00",
                    "party_size": 2,
                    "duration_minutes": None,
                    "nights": None,
                },
            )

        if any(word in customer_text for word in PRICE_WORDS):
            return self._call(AssistantToolName.GET_PRICE, {"item_name": "ხაჭაპური"})

        return say(ASSISTANT_TEXTS[language]["greeting"])

    def _after_tool(
        self,
        tool_name: str,
        result: JsonObject,
        language: str,
    ) -> ScriptedLlmTurn:
        texts: dict[str, str] = ASSISTANT_TEXTS[language]
        if tool_name == AssistantToolName.CHECK_AVAILABILITY:
            self.booking_request = {
                "name": "Нино",
                "phone": "+995 555 12 34 56",
                "resource_type": None,
                "date": "2026-10-06",
                "time": "19:00",
                "party_size": 2,
                "duration_minutes": None,
                "nights": None,
                "notes": "У окна",
            }
            return self._call(AssistantToolName.CREATE_BOOKING, self.booking_request)

        if tool_name == AssistantToolName.CREATE_BOOKING:
            return say(texts["booked"])

        if tool_name == AssistantToolName.GET_PRICE:
            matches: list[JsonObject] = result["matches"]
            if not matches:
                return say(texts["no_price"])

            return say(texts["price"].format(price=matches[0]["price_text"]))

        if tool_name == AssistantToolName.HANDOFF_TO_HUMAN:
            return say(str(result["customer_message"]))

        return say(texts["fine"])

    def _call(
        self, tool_name: AssistantToolName, arguments: JsonObject
    ) -> ScriptedLlmTurn:
        self.tool_calls.append(tool_name.value)
        return call_tool(tool_name, arguments)


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


class OverridableProvider(Protocol):
    def override(self, provider: object) -> object: ...


def replace_provider[Provided](
    provider: providers.Provider[Provided],
    value: Provided,
) -> None:
    """Make a container provider return a ready object (the test's edge)."""

    cast(OverridableProvider, provider).override(providers.Object(value))


def build_workshop_container(
    environment: Mapping[str, str],
    clock: MovableClock,
    otp: CapturingOtpDelivery,
    llm: ScriptedLlmAdapter,
    telegram: RecordedHttp,
    meta: RecordedHttp,
    elevenlabs: RecordedHttp,
    google: RecordedHttp,
    langfuse: RecordedHttp,
) -> AppContainer:
    """The real container with every edge replaced (nothing leaves the test)."""

    settings = assemble_app_settings(environment)
    container = AppContainer()
    replace_provider(container.config.app_settings, settings)
    replace_provider(container.time_provider.microsecond_wall_clock, clock.wall_clock)
    replace_provider(container.adapters.routing_llm_adapter, llm)
    replace_provider(container.facilitators.otp_delivery_facilitator, otp)
    replace_provider(
        container.clients.openai_responses_client,
        OpenAiResponsesClient(
            base_url=settings.openai_base_url,
            project_id=None,
            sdk_factory=refuse_openai_sdk,
        ),
    )
    replace_provider(
        container.clients.anthropic_messages_client,
        AnthropicMessagesClient(sdk_factory=refuse_anthropic_sdk),
    )
    replace_provider(
        container.clients.telegram_bot_client,
        TelegramBotClient(transport=build_transport(telegram, answer_telegram)),
    )
    replace_provider(
        container.clients.meta_graph_client,
        MetaGraphClient(transport=build_transport(meta, answer_with_empty_object)),
    )
    replace_provider(
        container.clients.elevenlabs_client,
        ElevenLabsClient(
            api_key=PlatformSecret("xi-e2e-key"),
            base_url=PublicBaseUrl(ELEVENLABS_BASE_URL),
            transport=build_transport(elevenlabs, answer_elevenlabs),
        ),
    )
    replace_provider(
        container.clients.google_calendar_client,
        GoogleCalendarClient(
            client_id=None,
            client_secret=None,
            redirect_url=None,
            transport=build_transport(google, answer_with_empty_object),
        ),
    )
    if (
        settings.langfuse_public_key is not None
        and settings.langfuse_secret_key is not None
    ):
        replace_provider(
            container.clients.langfuse_ingestion_client,
            LangfuseIngestionClient(
                host=settings.langfuse_host,
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                transport=build_transport(langfuse, answer_with_empty_object),
            ),
        )

    return container


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
