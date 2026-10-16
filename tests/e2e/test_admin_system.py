"""
The platform admin's system page and incident log on the real application:
only admins see them, the page counts the queue, and a data breach tells
the owners of the affected businesses (and nobody else) through the outbox.
"""

from collections.abc import Iterator
from typing import Any

import pytest

from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import ADMIN_EMAIL
from tests.e2e.journeys import sign_in_and_create_restaurant

type JsonObject = dict[str, Any]

OTHER_OWNER_PHONE: str = "+995 555 00 11 22"
SYSTEM_URL: str = "/v1/admin/system"
INCIDENTS_URL: str = "/v1/admin/incidents"
BREACH_NATURE: str = "A support export with customer names was e-mailed wrongly."


@pytest.fixture
def workshop() -> Iterator[Workshop]:
    running = start_workshop()
    with running.client:
        yield running


def second_business(workshop: Workshop) -> str:
    token, _ = workshop.sign_in_with_phone(OTHER_OWNER_PHONE)
    created = workshop.client.post(
        "/v1/businesses",
        json={"name": "Café Lumière", "niche_key": "restaurant"},
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


def notice(language: str, nature: str) -> JsonObject:
    return {
        "language": language,
        "nature": nature,
        "subject_categories": "Customers who booked by WhatsApp",
        "record_categories": "Names and phone numbers",
        "likely_consequences": "Unwanted calls are possible.",
        "measures": "The recipient deleted the file; exports now need review.",
    }


def breach_body(business_id: str, started_at: int) -> JsonObject:
    return {
        "kind": "data_breach",
        "severity": "sev1",
        "title": "Customer export sent to the wrong address",
        "started_at": started_at,
        "affected_business_ids": [business_id],
        "approximate_subject_count": 40,
        "approximate_record_count": 80,
        "notice_texts": [
            notice("en", BREACH_NATURE),
            notice("ru", "Выгрузка с именами клиентов ушла не тому адресату."),
            notice("ka", "კლიენტების სახელები შეცდომით გაიგზავნა."),
        ],
    }


def outbox_of(workshop: Workshop, business_id: str) -> list[OutboundMessageDocument]:
    messages = workshop.container.adapters.collections.outbound_message_collection()
    with workshop.container.utilities.storage_scope().platform_wide():
        stored = messages.list_all()
    return [message for message in stored if str(message.business_id) == business_id]


def incident_audit(workshop: Workshop, business_id: str) -> list[AuditLogEntryDocument]:
    entries = workshop.container.adapters.collections.audit_log_entry_collection()
    with workshop.container.utilities.storage_scope().platform_wide():
        stored = entries.list_all()
    return [
        entry
        for entry in stored
        if str(entry.business_id) == business_id and str(entry.entity) == "incident"
    ]


def test_only_the_admin_sees_the_system_page(workshop: Workshop) -> None:
    owner_token, _, _ = sign_in_and_create_restaurant(workshop)
    admin_token, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
    workshop.container.gateways.background_worker().run_once()

    page = workshop.client.get(SYSTEM_URL, headers=bearer(admin_token))
    refused = workshop.client.get(SYSTEM_URL, headers=bearer(owner_token))
    anonymous = workshop.client.get(SYSTEM_URL)

    assert page.status_code == 200, page.text
    view: JsonObject = page.json()
    assert [lane["lane"] for lane in view["lanes"]] == [
        "inbound",
        "outbound",
        "default",
        "autotests",
    ]
    assert all(lane["dead"] == 0 for lane in view["lanes"])
    [worker] = view["workers"]
    assert worker["is_stale"] is False and worker["age_seconds"] == 0
    # The in-memory store has no database to measure, and nothing backs up.
    assert view["database_bytes"] is None and view["tables"] == []
    assert view["last_backup"] is None and view["is_backup_overdue"] is True
    assert view["channels_in_error"] == [] and view["alerts"] == []
    assert refused.status_code == 403
    assert anonymous.status_code == 401


def test_a_breach_notifies_the_affected_owners_only(workshop: Workshop) -> None:
    _, _, affected_id = sign_in_and_create_restaurant(workshop)
    bystander_id = second_business(workshop)
    admin_token, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
    started_at = int(workshop.clock.wall_clock.now_unix()) - 3_600_000_000

    created = workshop.client.post(
        INCIDENTS_URL,
        json=breach_body(affected_id, started_at),
        headers=bearer(admin_token),
    )
    workshop.run_queued_jobs()
    listed = workshop.client.get(INCIDENTS_URL, headers=bearer(admin_token))

    assert created.status_code == 201, created.text
    incident: JsonObject = created.json()
    assert incident["notified_owner_count"] == 1
    assert incident["affected_business_ids"] == [affected_id]
    assert incident["notice_languages"] == ["en", "ru", "ka"]
    [sent] = outbox_of(workshop, affected_id)
    assert sent.staff_contact is not None
    assert sent.staff_contact.channel.value == "sms"
    assert "Customer export sent to the wrong address" in str(sent.text)
    assert str(incident["id"]) in str(sent.idempotency_key)
    assert outbox_of(workshop, bystander_id) == []
    [entry] = incident_audit(workshop, affected_id)
    assert str(entry.entity_id) == incident["id"]
    assert incident_audit(workshop, bystander_id) == []
    assert [item["id"] for item in listed.json()["items"]] == [incident["id"]]


def test_an_incident_needs_a_complete_notice_and_known_businesses(
    workshop: Workshop,
) -> None:
    owner_token, _, business_id = sign_in_and_create_restaurant(workshop)
    admin_token, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
    started_at = int(workshop.clock.wall_clock.now_unix())
    without_english = breach_body(business_id, started_at)
    without_english["notice_texts"] = [notice("ru", "Выгрузка ушла не туда.")]
    unknown = breach_body("business_00000000000000000000000000", started_at)
    outage = {
        "kind": "outage",
        "severity": "sev2",
        "title": "Replies delayed",
        "started_at": started_at,
        "affected_business_ids": [business_id],
    }

    refused = workshop.client.post(
        INCIDENTS_URL, json=without_english, headers=bearer(admin_token)
    )
    missing = workshop.client.post(
        INCIDENTS_URL, json=unknown, headers=bearer(admin_token)
    )
    by_owner = workshop.client.post(
        INCIDENTS_URL, json=outage, headers=bearer(owner_token)
    )
    recorded = workshop.client.post(
        INCIDENTS_URL, json=outage, headers=bearer(admin_token)
    )

    assert refused.status_code == 422, refused.text
    assert missing.status_code == 422, missing.text
    assert by_owner.status_code == 403
    assert recorded.status_code == 201, recorded.text
    assert recorded.json()["notified_owner_count"] == 0
    assert outbox_of(workshop, business_id) == []
    assert len(incident_audit(workshop, business_id)) == 1
