"""
The niche template editor on the real application: a platform admin
rewords a question of the restaurant template in Russian (and in English),
publishes it after the fresh sign-in's confirmation, new owners read it in
the catalog and the profile wizard, an assistant's prompt stays as it was,
and a reset brings back the code's wording; every publish is in the
platform's audit log.
"""

from collections.abc import Iterator
from typing import Any

import pytest

from app.schemas.domain.compliance import AuditLogEntryDocument
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import ADMIN_EMAIL
from tests.e2e.journeys import WIZARD_STEPS, sign_in_and_create_restaurant

type JsonObject = dict[str, Any]

EDITOR: str = "/v1/admin/niche-templates/restaurant"
CODE_LABEL_RU: str = "Какая у вас кухня?"
NEW_LABEL_RU: str = "Какую кухню вы готовите?"


@pytest.fixture
def workshop() -> Iterator[Workshop]:
    running = start_workshop()
    with running.client:
        yield running


def catalog_label(workshop: Workshop, language: str) -> str:
    answer = workshop.client.get(
        "/v1/catalog/niches/restaurant", params={"language": language}
    )
    assert answer.status_code == 200, answer.text
    return str(answer.json()["questions"][0]["label"])


def assembled_prompt(workshop: Workshop, base: str, token: str) -> str:
    version = workshop.client.post(
        f"{base}/assistant-versions", json={}, headers=bearer(token)
    )
    assert version.status_code == 201, version.text
    # The worker plays the version's autotests, so another can be assembled.
    workshop.container.gateways.background_worker().run_once()
    return str(version.json()["prompt_text"])


def owner_with_profile(workshop: Workshop) -> tuple[str, str]:
    token, _, business_id = sign_in_and_create_restaurant(workshop)
    base = f"/v1/businesses/{business_id}"
    for step, body in WIZARD_STEPS.items():
        saved = workshop.client.put(
            f"{base}/profile/steps/{step}", json=body, headers=bearer(token)
        )
        assert saved.status_code == 200, (step, saved.text)
    return token, base


def save_draft(
    workshop: Workshop, admin: dict[str, str], language: str, texts: dict[str, str]
) -> JsonObject:
    answer = workshop.client.put(
        f"{EDITOR}/draft",
        json={
            "language": language,
            "texts": [{"field_key": key, "text": text} for key, text in texts.items()],
        },
        headers=admin,
    )
    assert answer.status_code == 200, answer.text
    return dict(answer.json())


def test_an_admin_rewords_publishes_and_resets_a_niche_question(
    workshop: Workshop,
) -> None:
    client = workshop.client
    admin_token, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
    admin = bearer(admin_token)
    owner_token, base = owner_with_profile(workshop)
    prompt_before = assembled_prompt(workshop, base, owner_token)

    overview = client.get(
        "/v1/admin/niche-templates", params={"language": "ru"}, headers=admin
    )
    assert overview.status_code == 200, overview.text
    assert len(overview.json()["items"]) == 16
    assert overview.json()["items"][0]["published_version"] == 0

    editor = save_draft(
        workshop, admin, "ru", {"questions.cuisine.label": NEW_LABEL_RU}
    )
    assert editor["status"]["has_draft"] is True
    save_draft(
        workshop,
        admin,
        "en",
        {
            "questions.cuisine.label": "Which cuisine do you cook?",
            "handoff_rules.1": "A complaint about the food or the service",
        },
    )
    # A draft is the admin's alone.
    assert catalog_label(workshop, "ru") == CODE_LABEL_RU

    published = client.post(f"{EDITOR}/publish", headers=admin)
    assert published.status_code == 200, published.text
    assert (published.json()["version"], published.json()["kind"]) == (1, "publish")
    assert published.json()["override_count"] == 3

    assert catalog_label(workshop, "ru") == NEW_LABEL_RU
    assert catalog_label(workshop, "en") == "Which cuisine do you cook?"
    wizard = client.get(
        f"{base}/profile/wizard", params={"language": "ru"}, headers=bearer(owner_token)
    )
    assert wizard.status_code == 200, wizard.text
    labels = [
        question["question"]["label"]
        for step in wizard.json()["steps"]
        for question in step["questions"]
    ]
    assert NEW_LABEL_RU in labels
    # The assistant reads the code template: its prompt does not change.
    assert assembled_prompt(workshop, base, owner_token) == prompt_before

    reset = client.post(f"{EDITOR}/revert", json={"version": 0}, headers=admin)
    assert reset.status_code == 200, reset.text
    assert (reset.json()["version"], reset.json()["kind"]) == (2, "reset")
    assert catalog_label(workshop, "ru") == CODE_LABEL_RU

    history = client.get(f"{EDITOR}/versions", headers=admin)
    assert [item["version"] for item in history.json()["items"]] == [2, 1]
    assert niche_audit_references(workshop) == [
        "restaurant:v1:publish",
        "restaurant:v2:reset",
    ]


def niche_audit_references(workshop: Workshop) -> list[str]:
    collection = workshop.container.adapters.collections.audit_log_entry_collection()
    with workshop.container.utilities.storage_scope().platform_wide():
        stored = collection.list_all()
    entries: list[AuditLogEntryDocument] = sorted(
        (entry for entry in stored if str(entry.entity) == "niche_template"),
        key=lambda entry: int(entry.created_at),
    )
    return [str(entry.entity_id) for entry in entries]


def test_the_editor_refuses_owners_html_and_unknown_versions(
    workshop: Workshop,
) -> None:
    client = workshop.client
    admin = bearer(workshop.sign_in_with_email(ADMIN_EMAIL)[0])
    owner_token, _, _ = sign_in_and_create_restaurant(workshop)

    as_owner = client.get("/v1/admin/niche-templates", headers=bearer(owner_token))
    with_html = client.put(
        f"{EDITOR}/draft",
        json={
            "language": "ru",
            "texts": [{"field_key": "questions.cuisine.label", "text": "<b>Кухня</b>"}],
        },
        headers=admin,
    )
    unknown_field = client.put(
        f"{EDITOR}/draft",
        json={
            "language": "ru",
            "texts": [{"field_key": "prompt_rules.1", "text": "x"}],
        },
        headers=admin,
    )
    unknown_niche = client.get("/v1/admin/niche-templates/bakery", headers=admin)
    unknown_version = client.post(
        f"{EDITOR}/revert", json={"version": 9}, headers=admin
    )
    nothing_to_publish = client.post(f"{EDITOR}/publish", headers=admin)

    assert as_owner.status_code == 403, as_owner.text
    assert with_html.status_code == 422, with_html.text
    assert unknown_field.status_code == 422, unknown_field.text
    assert unknown_niche.status_code == 404, unknown_niche.text
    assert unknown_version.status_code == 404, unknown_version.text
    assert nothing_to_publish.status_code == 409, nothing_to_publish.text
