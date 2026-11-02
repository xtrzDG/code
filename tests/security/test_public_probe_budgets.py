"""
The public routes every page load or prober reaches are cheap: the widget's
config is cacheable and held to a budget per client network, /readyz shares
one check between probes and holds the internet to a budget too, while the
platform's own health check (a private address) is never refused.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateways.http.channel_routes import (
    WIDGET_CONFIG_REQUESTS_PER_MINUTE,
    build_channel_router,
)
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.health_routes import (
    READINESS_PROBES_PER_MINUTE,
    build_readiness_router,
)
from app.schemas.constants.observability import ReadinessState
from app.schemas.dto.channels.widget import WidgetConfigView
from app.schemas.dto.health import ReadinessQuery, ReadinessReport
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.channels.booleans import IsWebChatEnabled
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.platform.readiness_fakes import healthy_probe
from tests.platform.test_readiness_check import check

BUSINESS: BusinessId = BusinessId()


class ConfigOperator:
    def __init__(self) -> None:
        self.calls: int = 0

    def operate(self, input_data: BusinessId) -> WidgetConfigView:
        self.calls += 1
        return WidgetConfigView(
            business_id=input_data,
            business_name=BusinessName("Trattoria"),
            is_enabled=IsWebChatEnabled(True),
            default_language=LanguageTag("it"),
            languages=[],
            greetings=[],
        )


class Unused:
    def operate(self, input_data: object) -> object:
        raise AssertionError(input_data)


class CountingReadiness:
    def __init__(self) -> None:
        self.calls: int = 0

    def operate(self, input_data: ReadinessQuery) -> ReadinessReport:
        self.calls += 1
        report: ReadinessReport = check(healthy_probe())
        assert report.status is ReadinessState.READY
        del input_data
        return report


def config_client(address: str) -> tuple[TestClient, ConfigOperator]:
    operator = ConfigOperator()
    application = FastAPI()
    install_error_handlers(application)
    application.include_router(
        build_channel_router(
            telegram_webhook_operator=Unused(),
            meta_webhook_verification_operator=Unused(),
            meta_webhook_operator=Unused(),
            platform_bot_webhook_operator=Unused(),
            widget_config_operator=operator,
            widget_message_operator=Unused(),
            widget_messages_operator=Unused(),
        )
    )
    return TestClient(application, client=(address, 40000)), operator


def test_the_widget_config_is_cacheable_and_held_per_network() -> None:
    client, operator = config_client("198.51.100.7")
    path = f"/v1/widget/{BUSINESS}/config"

    answers = [client.get(path) for _ in range(WIDGET_CONFIG_REQUESTS_PER_MINUTE + 1)]

    assert answers[0].status_code == 200
    assert answers[0].headers["Cache-Control"] == "public, max-age=60"
    assert answers[0].headers["Vary"] == "Origin"
    assert answers[0].headers["Access-Control-Allow-Origin"] == "*"
    assert {answer.status_code for answer in answers[:-1]} == {200}
    refused = answers[-1]
    assert refused.status_code == 429
    assert refused.json()["error"] == "rate_limited"
    assert int(refused.headers["Retry-After"]) >= 1
    assert "public" not in refused.headers.get("Cache-Control", "")
    assert operator.calls == WIDGET_CONFIG_REQUESTS_PER_MINUTE


def probe_client(address: str, now: list[float]) -> tuple[TestClient, CountingReadiness]:
    readiness = CountingReadiness()
    application = FastAPI()
    install_error_handlers(application)
    application.include_router(build_readiness_router(readiness, clock=lambda: now[0]))
    return TestClient(application, client=(address, 40000)), readiness


def test_probes_within_two_seconds_share_one_check() -> None:
    now: list[float] = [100.0]
    client, readiness = probe_client("10.0.0.5", now)

    first = [client.get("/readyz") for _ in range(5)]
    now[0] += 2.5
    later = client.get("/readyz")

    assert {answer.status_code for answer in first} == {200}
    assert later.status_code == 200
    assert later.json()["status"] == "ready"
    assert readiness.calls == 2


def test_the_internet_is_held_to_a_probe_budget_and_render_never() -> None:
    now: list[float] = [100.0]
    # A public address (the documentation ranges count as private).
    public, _ = probe_client("93.184.216.34", now)
    render, _ = probe_client("10.0.0.5", now)

    public_answers = [
        public.get("/readyz") for _ in range(READINESS_PROBES_PER_MINUTE + 1)
    ]
    render_answers = [
        render.get("/readyz") for _ in range(READINESS_PROBES_PER_MINUTE * 2)
    ]

    assert public_answers[-1].status_code == 429
    assert public_answers[-1].json()["error"] == "rate_limited"
    assert {answer.status_code for answer in public_answers[:-1]} == {200}
    assert {answer.status_code for answer in render_answers} == {200}
