"""
The public status page and the admin's announcements on the real
application: anyone reads the status, only platform admins announce, and
the job records the day.
"""

from collections.abc import Iterator
from typing import Any

import pytest

from app.schemas.domain.compliance import AuditLogEntryDocument
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import ADMIN_EMAIL

type JsonObject = dict[str, Any]

STATUS_URL: str = "/v1/platform/status"
ANNOUNCEMENTS_URL: str = "/v1/admin/announcements"
OWNER_PHONE: str = "+995 555 12 34 56"
OUTAGE: JsonObject = {
    "level": "outage",
    "components": ["meta"],
    "messages": [
        {"language": "en", "text": "WhatsApp replies are delayed."},
        {"language": "ru", "text": "Ответы в WhatsApp задерживаются."},
        {"language": "ka", "text": "WhatsApp-ში პასუხები გვიანდება."},
    ],
}


@pytest.fixture
def workshop() -> Iterator[Workshop]:
    running = start_workshop()
    with running.client:
        yield running


def announcement_audit(workshop: Workshop) -> list[AuditLogEntryDocument]:
    entries = workshop.container.adapters.collections.audit_log_entry_collection()
    with workshop.container.utilities.storage_scope().platform_wide():
        stored = entries.list_all()
    return [entry for entry in stored if str(entry.entity) == "platform_announcement"]


def test_anyone_reads_the_status_of_a_quiet_platform(workshop: Workshop) -> None:
    response = workshop.client.get(STATUS_URL, params={"language": "ka"})

    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "public, max-age=30"
    view: JsonObject = response.json()
    assert view["level"] == "operational"
    assert [item["component"] for item in view["components"]] == [
        "chat",
        "meta",
        "telegram",
        "voice",
        "cabinet",
    ]
    assert len(view["components"][0]["history"]) == 90
    assert view["announcements"] == [] and view["past_announcements"] == []
    assert workshop.client.get(STATUS_URL, params={"language": "?"}).status_code == 422


def test_an_admin_announces_an_outage_and_resolves_it(workshop: Workshop) -> None:
    admin_token, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
    headers = bearer(admin_token)

    created = workshop.client.post(ANNOUNCEMENTS_URL, json=OUTAGE, headers=headers)
    during = workshop.client.get(STATUS_URL, params={"language": "ru"}).json()
    workshop.container.gateways.background_worker().run_once()
    resolved = workshop.client.patch(
        f"{ANNOUNCEMENTS_URL}/{created.json()['id']}",
        json={"resolve": True},
        headers=headers,
    )
    after = workshop.client.get(STATUS_URL).json()
    listed = workshop.client.get(ANNOUNCEMENTS_URL, headers=headers)

    assert created.status_code == 201, created.text
    assert during["level"] == "outage"
    assert during["announcements"][0]["text"] == "Ответы в WhatsApp задерживаются."
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "resolved"
    assert after["level"] == "operational"
    assert after["past_announcements"][0]["id"] == created.json()["id"]
    meta = next(item for item in after["components"] if item["component"] == "meta")
    assert meta["history"][-1]["level"] == "outage"  # the job recorded the day
    assert [item["id"] for item in listed.json()["items"]] == [created.json()["id"]]
    assert [entry.action.value for entry in announcement_audit(workshop)] == [
        "create",
        "update",
    ]


def test_only_platform_admins_announce(workshop: Workshop) -> None:
    owner_token, _ = workshop.sign_in_with_phone(OWNER_PHONE)

    refused = workshop.client.post(
        ANNOUNCEMENTS_URL, json=OUTAGE, headers=bearer(owner_token)
    )
    anonymous = workshop.client.get(ANNOUNCEMENTS_URL)

    assert refused.status_code == 403
    assert anonymous.status_code == 401


def test_an_announcement_needs_english_and_components(workshop: Workshop) -> None:
    admin_token, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
    headers = bearer(admin_token)

    without_english = workshop.client.post(
        ANNOUNCEMENTS_URL,
        json={**OUTAGE, "messages": OUTAGE["messages"][1:]},
        headers=headers,
    )
    without_components = workshop.client.post(
        ANNOUNCEMENTS_URL, json={**OUTAGE, "components": []}, headers=headers
    )
    unknown = workshop.client.patch(
        f"{ANNOUNCEMENTS_URL}/not-an-id", json={"resolve": True}, headers=headers
    )

    assert without_english.status_code == 422
    assert without_components.status_code == 422
    assert unknown.status_code == 404
