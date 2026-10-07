"""
The demo tells one truth: every number the cabinet and the admin show is
computed from the seeded records themselves, so no two screens disagree.

- package usage = the seeded calls (minutes rounded up) and conversations;
- every connected channel has a public address and a share link;
- the admin's autotest health is the published version's stored verdict;
- the inbox badge is the sum of the inbox tabs it stands for;
- a client with provider costs has a margin;
- the customer list comes most recently active first, as each row says.
"""

import math
from typing import Any, cast

from fastapi.testclient import TestClient

from app.schemas.domain.conversations import CallDocument
from tests.demo.test_demo_seeding import (
    DEMO_ENVIRONMENT,
    RESTAURANT,
    SALON,
    businesses_by_name,
    sign_in_owner,
)
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import ADMIN_EMAIL

type JsonObject = dict[str, Any]

# Channels whose customers open a chat from a link (the web chat is the
# hosted page itself).
LINKED_CHANNELS: frozenset[str] = frozenset(
    {"whatsapp", "telegram", "instagram", "messenger", "phone"}
)
MAX_PAGE: int = 100


def read(client: TestClient, path: str, headers: dict[str, str]) -> Any:
    response = client.get(path, headers=headers)
    assert response.status_code == 200, (path, response.text)
    return response.json()


def seeded_calls(workshop: Workshop, business_id: str) -> list[CallDocument]:
    container = workshop.container
    with container.utilities.storage_scope().platform_wide():
        calls = container.adapters.collections.call_collection().list_all()
    return [call for call in calls if str(call.business_id) == business_id]


def view_size(
    client: TestClient, business_id: str, view: str, headers: dict[str, str]
) -> int:
    page: JsonObject = read(
        client,
        f"/v1/businesses/{business_id}/inbox?view={view}&limit={MAX_PAGE}",
        headers,
    )
    items = cast(list[JsonObject], page["items"])
    assert page["next_cursor"] is None, "the demo inbox fits one page"
    return len(items)


def test_package_usage_is_what_the_seeded_calls_and_chats_metered() -> None:
    workshop = start_workshop(DEMO_ENVIRONMENT)
    with workshop.client as client:
        headers = sign_in_owner(workshop)
        for name, business in businesses_by_name(client, headers).items():
            base = f"/v1/businesses/{business['id']}"
            dashboard: JsonObject = read(client, f"{base}/dashboard", headers)
            billing: JsonObject = read(client, f"{base}/billing", headers)
            since = int(billing["subscription"]["period_start"])
            seconds = sum(
                int(call.duration_seconds)
                for call in seeded_calls(workshop, str(business["id"]))
                if int(call.started_at) >= since
            )

            package: JsonObject = dashboard["package"]
            assert int(package["used_voice_minutes"]) == math.ceil(seconds / 60), name
            assert int(package["used_dialogs"]) > 0, name
            if name == RESTAURANT:
                assert seconds > 0, "the restaurant's calls fall in its trial"


def test_every_connected_channel_has_an_address_and_a_share_link() -> None:
    workshop = start_workshop(DEMO_ENVIRONMENT)
    with workshop.client as client:
        headers = sign_in_owner(workshop)
        for name, business in businesses_by_name(client, headers).items():
            base = f"/v1/businesses/{business['id']}"
            channels = cast(list[JsonObject], read(client, f"{base}/channels", headers))
            shared: JsonObject = read(client, f"{base}/share-links", headers)
            links: dict[str, JsonObject] = {
                str(link["kind"]): link for link in shared["links"]
            }

            connected = [
                channel
                for channel in channels
                if channel["status"] == "connected"
                and channel["channel"] in LINKED_CHANNELS
            ]
            assert connected, name
            for channel in connected:
                kind = str(channel["channel"])
                assert channel["link_state"] == "linked", (name, kind)
                assert links[kind]["url"], (name, kind, links[kind])
                assert links[kind]["gap"] is None, (name, kind)


def test_the_inbox_badge_is_the_sum_of_its_tabs() -> None:
    workshop = start_workshop(DEMO_ENVIRONMENT)
    with workshop.client as client:
        headers = sign_in_owner(workshop)
        for name, business in businesses_by_name(client, headers).items():
            business_id = str(business["id"])
            base = f"/v1/businesses/{business_id}"
            attention: JsonObject = read(client, f"{base}/attention-counts", headers)
            tabs: JsonObject = read(client, f"{base}/inbox/counts", headers)

            needs_person = view_size(client, business_id, "needs_person", headers)
            requests = view_size(client, business_id, "requests", headers)
            for counts in (attention, tabs):
                assert (counts["needs_person"], counts["requests"]) == (
                    needs_person,
                    requests,
                ), name
                assert counts["unassigned"] == view_size(
                    client, business_id, "unassigned", headers
                ), name
            if name == RESTAURANT:
                assert needs_person + requests > 0


def test_admin_health_and_margin_agree_with_the_cabinet() -> None:
    workshop = start_workshop(DEMO_ENVIRONMENT)
    with workshop.client as client:
        owner = sign_in_owner(workshop)
        businesses = businesses_by_name(client, owner)
        admin_token, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
        admin = bearer(admin_token)
        for name in (RESTAURANT, SALON):
            business_id = str(businesses[name]["id"])
            base = f"/v1/businesses/{business_id}"
            versions = cast(
                list[JsonObject], read(client, f"{base}/assistant-versions", owner)
            )
            published = next(v for v in versions if v["status"] == "published")
            run: JsonObject = read(
                client,
                f"{base}/assistant-versions/{published['id']}/autotest-run",
                owner,
            )
            detail: JsonObject = read(client, f"/v1/admin/clients/{business_id}", admin)

            summary: JsonObject = detail["summary"]
            verdict: JsonObject = summary["autotest_verdict"]
            assert verdict["version_number"] == published["version_number"], name
            assert verdict["is_passed"] is run["is_passed"], name
            assert ("autotests_failed" in summary["health_issues"]) is (
                not run["is_passed"]
            ), name
            cost: JsonObject = summary["cost"]
            assert int(cost["provider_cost_micro_usd"]) > 0, name
            assert cost["provider_cost"] is not None, name
            assert cost["margin"] is not None, name
            assert cost["exchange_rate"] is not None, name


def test_the_customer_list_comes_most_recently_active_first() -> None:
    workshop = start_workshop(DEMO_ENVIRONMENT)
    with workshop.client as client:
        headers = sign_in_owner(workshop)
        for name, business in businesses_by_name(client, headers).items():
            page: JsonObject = read(
                client,
                f"/v1/businesses/{business['id']}/contacts?limit={MAX_PAGE}",
                headers,
            )

            moments = [int(item["last_activity_at"]) for item in page["items"]]
            assert len(moments) > 1, name
            assert moments == sorted(moments, reverse=True), name
