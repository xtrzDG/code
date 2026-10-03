"""
POST /v1/telemetry/events over the real API: batches of Web Vitals and
tunnel steps from a signed-in person, at most 50 at once and 30 batches a
minute; a tunnel step names a business only of the person's own team.
"""

from typing import Any

from typed_time_provider import Microseconds

from app.schemas.constants.analytics import (
    DeviceClass,
    ProductEventName,
    ProductEventSource,
    TunnelStepKey,
    WebVitalName,
)
from app.schemas.typings.analytics.constrained_integers import WebVitalValue
from tests.analytics.test_launch_journey_events import named, stored_events
from tests.e2e.harness import Workshop
from tests.setup.launch_steps import create_assistant

VITAL: dict[str, Any] = {
    "kind": "web_vital",
    "metric": "inp",
    "value": 180,
    "route": "/b/[businessId]/inbox",
    "device_class": "mobile",
}
TELEMETRY: str = "/v1/telemetry/events"
SECOND_OWNER_PHONE: str = "+995 555 98 76 54"


def step(name: str, action: str, business_id: str | None = None) -> dict[str, Any]:
    report: dict[str, Any] = {"kind": "tunnel_step", "step": name, "action": action}
    if business_id is not None:
        report["business_id"] = business_id
    return report


def test_a_batch_keeps_vitals_and_tunnel_steps(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)

    sent = workshop.client.post(
        TELEMETRY,
        json={
            "events": [
                VITAL,
                {**VITAL, "metric": "cls", "value": 900, "device_class": "desktop"},
                step("business", "entered"),
                step("hours", "completed", assistant.business_id),
            ]
        },
        headers=assistant.headers,
    )

    assert sent.status_code == 202, sent.text
    assert sent.json() == {"web_vitals": 2, "tunnel_steps": 2}
    now = workshop.clock.wall_clock.now_unix()
    counts = workshop.container.repositories.web_vital_sample_repo().count_buckets(
        WebVitalName.INP,
        now,
        Microseconds(int(now) + 1),
        [WebVitalValue(0), WebVitalValue(100), WebVitalValue(200)],
    )
    assert [(int(c.bucket), int(c.count), c.device_class) for c in counts] == [
        (1, 1, DeviceClass.MOBILE)
    ]
    entered = named(stored_events(workshop), ProductEventName.TUNNEL_STEP_ENTERED)
    assert [(e.properties.tunnel_step, e.business_id, e.source) for e in entered] == [
        (TunnelStepKey.BUSINESS, None, ProductEventSource.CABINET)
    ]
    (completed,) = named(
        stored_events(workshop), ProductEventName.TUNNEL_STEP_COMPLETED
    )
    assert str(completed.business_id) == assistant.business_id
    assert str(completed.user_id) == assistant.owner_id


def test_a_step_naming_another_teams_business_keeps_no_business(
    workshop: Workshop,
) -> None:
    georgian = create_assistant(workshop)
    workshop.clock.advance(60)
    other = create_assistant(workshop, phone=SECOND_OWNER_PHONE)

    sent = workshop.client.post(
        TELEMETRY,
        json={"events": [step("offer", "entered", georgian.business_id)]},
        headers=other.headers,
    )

    assert sent.status_code == 202, sent.text
    (entered,) = named(stored_events(workshop), ProductEventName.TUNNEL_STEP_ENTERED)
    assert entered.business_id is None
    assert str(entered.user_id) == other.owner_id


def test_reports_need_a_session_and_a_valid_batch(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    headers = assistant.headers

    assert workshop.client.post(TELEMETRY, json={"events": [VITAL]}).status_code == 401
    refused_bodies: list[dict[str, Any]] = [
        {"events": []},
        {"events": [VITAL] * 51},
        {"events": [{**VITAL, "kind": "click"}]},
        {"events": [{**VITAL, "metric": "fid"}]},
        {"events": [{**VITAL, "value": -1}]},
        {"events": [{**VITAL, "route": "https://example.com/b/1"}]},
        {"events": [{**VITAL, "user_id": "someone"}]},
        {"events": [step("payment", "entered")]},
    ]
    for body in refused_bodies:
        refused = workshop.client.post(TELEMETRY, json=body, headers=headers)
        assert refused.status_code == 422, (body, refused.text)


def test_thirty_batches_a_minute_then_429(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)

    for _ in range(30):
        sent = workshop.client.post(
            TELEMETRY, json={"events": [VITAL]}, headers=assistant.headers
        )
        assert sent.status_code == 202, sent.text

    refused = workshop.client.post(
        TELEMETRY, json={"events": [VITAL]}, headers=assistant.headers
    )
    assert refused.status_code == 429, refused.text
    retry_after = int(refused.headers["Retry-After"])
    assert 0 < retry_after <= 120

    workshop.clock.advance(retry_after)
    again = workshop.client.post(
        TELEMETRY, json={"events": [VITAL]}, headers=assistant.headers
    )
    assert again.status_code == 202, again.text
