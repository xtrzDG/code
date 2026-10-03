"""
Steps of the guided launch over the real API: "Create an AI assistant", the
profile a Georgian restaurant fills, its staff contact, the agreement,
"Apply changes" and reading the setup.
"""

from dataclasses import dataclass
from typing import Any

from tests.e2e.harness import Workshop, bearer
from tests.e2e.journeys import GEORGIAN_OWNER_PHONE, WIZARD_STEPS

type JsonObject = dict[str, Any]

STAFF_PHONE: str = "+995 555 77 66 55"
STAFF_CONTACT: JsonObject = {
    "name": "Гиорги",
    "channel": "telegram",
    "address": "70001",
    "language": "ru",
}


@dataclass(frozen=True)
class NewAssistant:
    """An owner's business made with "Create an AI assistant"."""

    token: str
    owner_id: str
    business_id: str
    created: JsonObject

    @property
    def base(self) -> str:
        return f"/v1/businesses/{self.business_id}"

    @property
    def headers(self) -> dict[str, str]:
        return bearer(self.token)


def create_assistant(
    workshop: Workshop,
    body: JsonObject | None = None,
    phone: str = GEORGIAN_OWNER_PHONE,
) -> NewAssistant:
    token, session = workshop.sign_in_with_phone(phone)
    created = workshop.client.post(
        "/v1/assistants",
        json=body or {"name": "Salobie Bia", "niche_key": "restaurant"},
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text
    payload: JsonObject = created.json()
    return NewAssistant(
        token=token,
        owner_id=str(session["user"]["id"]),
        business_id=str(payload["business"]["id"]),
        created=payload,
    )


def fill_profile(workshop: Workshop, assistant: NewAssistant) -> None:
    """Every wizard step of the restaurant, and a bookable table."""

    for step, body in WIZARD_STEPS.items():
        saved = workshop.client.put(
            f"{assistant.base}/profile/steps/{step}",
            json=body,
            headers=assistant.headers,
        )
        assert saved.status_code == 200, (step, saved.text)

    table = workshop.client.post(
        f"{assistant.base}/resources",
        json={"name": "Стол у окна", "capacity": 4, "unit_count": 3},
        headers=assistant.headers,
    )
    assert table.status_code == 201, table.text


def add_staff_contact(workshop: Workshop, assistant: NewAssistant) -> None:
    saved = workshop.client.patch(
        assistant.base,
        json={"manager_contacts": [STAFF_CONTACT]},
        headers=assistant.headers,
    )
    assert saved.status_code == 200, saved.text


def accept_dpa(workshop: Workshop, assistant: NewAssistant) -> None:
    accepted = workshop.client.post(
        f"{assistant.base}/dpa", json={}, headers=assistant.headers
    )
    assert accepted.status_code == 201, accepted.text


def make_launch_ready(workshop: Workshop, assistant: NewAssistant) -> None:
    """The profile, a staff contact and the agreement: all a launch needs."""

    fill_profile(workshop, assistant)
    add_staff_contact(workshop, assistant)
    accept_dpa(workshop, assistant)


def invite_staff(workshop: Workshop, assistant: NewAssistant) -> dict[str, str]:
    """A staff member of the business, signed in; their bearer header."""

    invited = workshop.client.post(
        f"{assistant.base}/members",
        json={"phone_number": STAFF_PHONE, "role": "staff"},
        headers=assistant.headers,
    )
    assert invited.status_code == 201, invited.text
    return bearer(workshop.sign_in_with_phone(STAFF_PHONE)[0])


def read_setup(
    workshop: Workshop,
    assistant: NewAssistant,
    language: str | None = None,
) -> JsonObject:
    read = workshop.client.get(
        f"{assistant.base}/setup",
        params={} if language is None else {"language": language},
        headers=assistant.headers,
    )
    assert read.status_code == 200, read.text
    return dict(read.json())


def step_statuses(setup: JsonObject) -> dict[str, str]:
    return {str(step["code"]): str(step["status"]) for step in setup["steps"]}


def step_of(setup: JsonObject, code: str) -> JsonObject:
    return next(dict(step) for step in setup["steps"] if step["code"] == code)


def apply_changes(workshop: Workshop, assistant: NewAssistant) -> JsonObject:
    applied = workshop.client.post(
        f"{assistant.base}/assistant/apply", headers=assistant.headers
    )
    assert applied.status_code == 202, applied.text
    return dict(applied.json())


def read_apply(
    workshop: Workshop,
    assistant: NewAssistant,
    language: str | None = None,
) -> JsonObject:
    read = workshop.client.get(
        f"{assistant.base}/assistant/apply",
        params={} if language is None else {"language": language},
        headers=assistant.headers,
    )
    assert read.status_code == 200, read.text
    return dict(read.json())


def go_live(workshop: Workshop, assistant: NewAssistant) -> JsonObject:
    """Apply changes and let the worker check and publish the version."""

    started: JsonObject = apply_changes(workshop, assistant)
    assert started["stage"] == "checking", started
    workshop.run_queued_jobs()
    live: JsonObject = read_apply(workshop, assistant)
    assert live["stage"] == "live", live
    return live
