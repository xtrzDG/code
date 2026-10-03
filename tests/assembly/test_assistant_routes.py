"""The owner's flow over HTTP: assemble, test, publish, roll back, narrowed runs."""

from typing import Any

from tests.assembly.assistant_routes_helpers import assemble, versions_url
from tests.assembly.georgian_restaurant_seed import seed_georgian_restaurant
from tests.assembly.international_business_seeds import seed_italian_restaurant
from tests.assembly.testbed import AssemblyTestbed


def test_owner_assembles_tests_publishes_and_rolls_back_over_http() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)
    client = testbed.build_client()
    owner = testbed.bearer(testbed.owner_id)
    base = versions_url(business.id)

    draft = assemble(client, owner, business.id, {"run_autotests": False})
    assert draft["version_number"] == 1
    assert draft["status"] == "draft"
    assert draft["prompt_text"].startswith("# Role\n")
    assert draft["facts"][0] == {
        "key": "business_name",
        "label": "Business name",
        "value": "Café Rustaveli",
    }
    assert "send_link" in draft["tools"]

    # The request only starts the run; the background worker plays it.
    started = client.post(f"{base}/{draft['id']}/autotests", headers=owner)
    assert started.status_code == 202, started.text
    assert started.json()["status"] == "running"
    assert started.json()["version_status"] == "testing"
    # The planned scenarios are known at once; results arrive as they play.
    assert started.json()["scenario_count"] == 29
    assert started.json()["results"] == []
    assert testbed.judge_requests.requests == []
    running = client.get(f"{base}/{draft['id']}/autotest-run", headers=owner)
    assert running.json()["status"] == "running"
    publishing_early = client.post(f"{base}/{draft['id']}/publish", headers=owner)
    assert publishing_early.status_code == 409

    tick = testbed.run_worker()

    assert (tick.queued_runs, tick.failures) == (1, 0)
    latest_run = client.get(f"{base}/{draft['id']}/autotest-run", headers=owner)
    assert latest_run.status_code == 200
    run: dict[str, Any] = latest_run.json()
    assert run["id"] == started.json()["id"]
    assert run["status"] == "finished"
    assert run["is_full_coverage"] is True
    assert run["version_status"] == "ready"
    assert run["is_passed"] is True
    assert run["scenario_count"] == 29
    assert run["results"][0]["transcript"][0]["author"] == "customer"

    published = client.post(f"{base}/{draft['id']}/publish", headers=owner)
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "published"
    assert published.json()["voice_agent_id"] == "agent_1"

    second = assemble(client, owner, business.id)
    assert second["status"] == "testing"
    testbed.run_worker()
    second = client.get(f"{base}/{second['id']}", headers=owner).json()
    assert second["status"] == "ready"
    assert second["test_score"] == 5.0
    assert client.post(f"{base}/{second['id']}/publish", headers=owner).json()[
        "status"
    ] == ("published")

    rolled_back = client.post(f"{base}/{draft['id']}/rollback", headers=owner)
    assert rolled_back.status_code == 200, rolled_back.text
    assert rolled_back.json()["status"] == "published"

    history = client.get(base, headers=owner)
    assert history.status_code == 200
    assert [(item["version_number"], item["status"]) for item in history.json()] == [
        (2, "archived"),
        (1, "published"),
    ]
    assert "prompt_text" not in history.json()[0]

    details = client.get(f"{base}/{second['id']}", headers=owner)
    assert details.status_code == 200
    assert details.json()["prompt_text"] == second["prompt_text"]


def test_autotests_can_be_narrowed_over_http() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    client = testbed.build_client()
    owner = testbed.bearer(testbed.owner_id)

    version = assemble(
        client,
        owner,
        business.id,
        {"languages": ["en"], "kinds": ["human_request", "price_question"]},
    )
    testbed.run_worker()
    run = client.get(
        f"{versions_url(business.id)}/{version['id']}/autotest-run",
        headers=owner,
    ).json()

    assert [result["scenario_key"] for result in run["results"]] == [
        "price_question__en",
        "human_request__en",
        "price_question__en__1",
        "price_question__en__2",
    ]
    # A passed narrowed run proves nothing about the other languages and
    # kinds: the version is not ready for customers.
    assert run["is_passed"] is True
    assert run["is_full_coverage"] is False
    assert run["version_status"] == "draft"
    rerun = client.post(
        f"{versions_url(business.id)}/{version['id']}/autotests",
        headers=owner,
        json={"languages": ["it"], "kinds": ["rude_customer"]},
    )
    assert rerun.status_code == 202
    testbed.run_worker()
    rerun_view = client.get(
        f"{versions_url(business.id)}/{version['id']}/autotest-run",
        headers=owner,
    ).json()
    assert [result["scenario_key"] for result in rerun_view["results"]] == [
        "rude_customer__it"
    ]


def test_failed_version_is_published_only_by_an_admin_with_acceptance() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    testbed.judge_raw_answers["booking__it"] = "not a verdict"
    client = testbed.build_client()
    owner = testbed.bearer(testbed.owner_id)
    admin = testbed.bearer(testbed.add_platform_admin())
    assembled = assemble(client, owner, business.id)
    testbed.run_worker()
    version = client.get(
        f"{versions_url(business.id)}/{assembled['id']}", headers=owner
    ).json()
    publish_url = f"{versions_url(business.id)}/{version['id']}/publish"

    refused = client.post(publish_url, headers=owner)
    forced_by_owner = client.post(
        publish_url,
        headers=owner,
        json={"accept_failed_tests": True},
    )
    accepted = client.post(
        publish_url,
        headers=admin,
        json={"accept_failed_tests": True},
    )

    assert version["status"] == "tests_failed"
    assert refused.status_code == 409
    assert refused.json()["error"] == "conflict"
    assert forced_by_owner.status_code == 403
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "published"
