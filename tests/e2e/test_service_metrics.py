"""
The service metrics end to end: GET /metrics only with METRICS_TOKEN, and
the counters a scripted Telegram conversation moves (webhook, pickup,
model call, stored answer, sent reply, request durations by route).
"""

from collections.abc import Iterator

import pytest
from prometheus_client.parser import text_string_to_metric_families

from tests.e2e.harness import Workshop, start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.e2e.journeys import BOOKING_REQUEST_RU, open_restaurant
from tests.e2e.telegram_customer import TelegramCustomer

METRICS_TOKEN: str = "test-token-0000"  # gitleaks:allow
METRICS_ENVIRONMENT: dict[str, str] = {
    **E2E_ENVIRONMENT,
    "METRICS_TOKEN": METRICS_TOKEN,
}
SCRAPE_HEADERS: dict[str, str] = {"Authorization": f"Bearer {METRICS_TOKEN}"}
TELEGRAM_WEBHOOK_ROUTE: str = "/v1/channels/telegram/{channel_id}/webhook"

type Labels = frozenset[tuple[str, str]]


@pytest.fixture
def metered_workshop() -> Iterator[Workshop]:
    workshop = start_workshop(METRICS_ENVIRONMENT)
    with workshop.client:
        yield workshop


def scrape(workshop: Workshop) -> dict[str, dict[Labels, float]]:
    """The page's samples: by sample name, then by label set."""

    page = workshop.client.get("/metrics", headers=SCRAPE_HEADERS)
    assert page.status_code == 200, page.text
    assert page.headers["content-type"].startswith("text/plain")
    samples: dict[str, dict[Labels, float]] = {}
    for family in text_string_to_metric_families(page.text):
        for sample in family.samples:
            samples.setdefault(sample.name, {})[frozenset(sample.labels.items())] = (
                sample.value
            )

    return samples


def value(samples: dict[str, dict[Labels, float]], name: str, **labels: str) -> float:
    """The sum of the samples of `name` whose labels include `labels`."""

    wanted: set[tuple[str, str]] = set(labels.items())
    return sum(
        sample
        for sample_labels, sample in samples.get(name, {}).items()
        if wanted <= sample_labels
    )


def test_metrics_need_the_token(metered_workshop: Workshop) -> None:
    client = metered_workshop.client

    anonymous = client.get("/metrics")
    wrong = client.get("/metrics", headers={"Authorization": "Bearer nope"})
    scraped = client.get("/metrics", headers=SCRAPE_HEADERS)

    assert anonymous.status_code == 401
    assert wrong.status_code == 401
    assert scraped.status_code == 200
    assert "workshop_http_request_duration_seconds" in scraped.text
    assert "/metrics" not in client.get("/openapi.json").json()["paths"]


def test_without_a_token_there_is_no_metrics_page(workshop: Workshop) -> None:
    refused = workshop.client.get("/metrics", headers=SCRAPE_HEADERS)

    assert refused.status_code == 404


def test_a_scripted_conversation_moves_the_counters(
    metered_workshop: Workshop,
) -> None:
    restaurant = open_restaurant(metered_workshop)
    before = scrape(metered_workshop)

    answers = TelegramCustomer(metered_workshop, restaurant).writes(BOOKING_REQUEST_RU)

    after = scrape(metered_workshop)
    assert answers, "the bot answered"

    def grew(name: str, **labels: str) -> float:
        return value(after, name, **labels) - value(before, name, **labels)

    assert grew("workshop_webhook_messages_total", channel="telegram") == 2
    assert (
        grew("workshop_webhook_messages_total", channel="telegram", outcome="received")
        == 1
    )
    assert (
        grew("workshop_webhook_messages_total", channel="telegram", outcome="queued")
        == 1
    )
    assert grew("workshop_job_pickup_delay_seconds_count", lane="inbound") >= 1
    assert grew("workshop_answer_latency_seconds_count", channel="telegram") == 1
    assert grew("workshop_llm_call_duration_seconds_count", outcome="ok") >= 1
    assert (
        grew(
            "workshop_outbound_attempts_total", provider="telegram", outcome="delivered"
        )
        >= 1
    )
    assert (
        grew(
            "workshop_http_request_duration_seconds_count",
            route=TELEGRAM_WEBHOOK_ROUTE,
            status_class="2xx",
        )
        == 1
    )
    assert value(after, "workshop_db_pool_connections_in_use") == 0
