"""
The facts a brand shares count wherever the location's own knowledge
counts, over the real API: the owner's test chat is rebuilt when a shared
fact changes, and the "what to add" list and the setup's offer step see a
FAQ and prices the location takes from its brand.
"""

from collections.abc import Iterator
from typing import Any

import pytest

from tests.e2e.harness import Workshop, start_workshop
from tests.setup.launch_steps import (
    NewAssistant,
    create_assistant,
    fill_profile,
    read_setup,
    step_statuses,
)

type JsonObject = dict[str, Any]

SHARED_FAQ: JsonObject = {
    "kind": "faq",
    "title": "Parking",
    "body": "Free parking behind the building.",
    "shared_key": "parking",
}
SHARED_DISH: JsonObject = {
    "kind": "menu_item",
    "title": "Khachapuri",
    "price_minor": 1800,
    "shared_key": "khachapuri",
}


@pytest.fixture
def workshop() -> Iterator[Workshop]:
    workshop = start_workshop()
    with workshop.client:
        yield workshop


def make_brand(workshop: Workshop, assistant: NewAssistant) -> str:
    created = workshop.client.post(
        "/v1/brands",
        json={"name": "Salobie Group", "business_id": assistant.business_id},
        headers=assistant.headers,
    )
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


def share(
    workshop: Workshop, assistant: NewAssistant, brand_id: str, fact: JsonObject
) -> None:
    shared = workshop.client.post(
        f"/v1/brands/{brand_id}/knowledge", json=fact, headers=assistant.headers
    )
    assert shared.status_code == 201, shared.text


def answering_version(workshop: Workshop, assistant: NewAssistant) -> int:
    """The owner's test chat answers; the version it answered with."""

    reply = workshop.client.post(
        f"{assistant.base}/test-chat",
        json={"text": "Здравствуйте!"},
        headers=assistant.headers,
    )
    assert reply.status_code == 200, reply.text
    return int(reply.json()["assistant_version_number"])


def drop_own_knowledge(workshop: Workshop, assistant: NewAssistant) -> None:
    """The wizard's FAQ and prices removed: the location keeps none of its own."""

    listed = workshop.client.get(
        f"{assistant.base}/knowledge",
        params={"limit": "100"},
        headers=assistant.headers,
    )
    assert listed.status_code == 200, listed.text
    for item in listed.json()["items"]:
        removed = workshop.client.delete(
            f"{assistant.base}/knowledge/{item['id']}", headers=assistant.headers
        )
        assert removed.status_code == 204, removed.text


def gap_kinds(workshop: Workshop, assistant: NewAssistant) -> set[str]:
    gaps = workshop.client.get(
        f"{assistant.base}/profile/gaps", headers=assistant.headers
    )
    assert gaps.status_code == 200, gaps.text
    return {str(gap["kind"]) for gap in gaps.json()["gaps"]}


def test_the_test_chat_is_rebuilt_when_a_shared_fact_changes(
    workshop: Workshop,
) -> None:
    assistant = create_assistant(workshop)
    fill_profile(workshop, assistant)
    first = answering_version(workshop, assistant)
    brand_id = make_brand(workshop, assistant)
    workshop.clock.advance(60)
    share(workshop, assistant, brand_id, SHARED_FAQ)

    after_sharing = answering_version(workshop, assistant)
    unchanged = answering_version(workshop, assistant)
    workshop.clock.advance(60)
    changed = workshop.client.put(
        f"/v1/brands/{brand_id}/knowledge/parking",
        json={**SHARED_FAQ, "body": "Parking is paid now."},
        headers=assistant.headers,
    )
    after_change = answering_version(workshop, assistant)

    assert changed.status_code == 200, changed.text
    assert (first, after_sharing, unchanged, after_change) == (1, 2, 2, 3)


def test_gaps_and_setup_count_what_the_brand_shares(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    fill_profile(workshop, assistant)
    drop_own_knowledge(workshop, assistant)
    brand_id = make_brand(workshop, assistant)
    before = gap_kinds(workshop, assistant)
    offer_before = step_statuses(read_setup(workshop, assistant))["offer"]

    share(workshop, assistant, brand_id, SHARED_FAQ)
    share(workshop, assistant, brand_id, SHARED_DISH)

    assert {"no_faq", "no_priced_items"} <= before
    assert offer_before != "done"
    assert gap_kinds(workshop, assistant).isdisjoint({"no_faq", "no_priced_items"})
    assert step_statuses(read_setup(workshop, assistant))["offer"] == "done"
