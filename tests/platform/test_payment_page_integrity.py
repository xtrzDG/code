"""
The payment pages' scripts are checked every week against their reviewed
inventory (PAY-02; PCI DSS 11.6.1 intent): a scheduled workflow with
pinned actions, read-only permissions and no secret hashes the files
production serves (with PRODUCTION_CABINET_URL) or a fresh build's, fails
on a difference and opens one issue; the schedule watch notices when it
stops running. The comparison itself is tested in
web/src/test/paymentPageScripts.test.ts.
"""

import json
import re
from typing import Any

from tests.platform.environment_sources import ROOT
from tests.platform.test_supply_chain_workflows import (
    scripts,
    steps,
    triggers,
    uses,
    workflow,
)

NAME = "payment-page-integrity.yml"
INVENTORY = ROOT / "web" / "payment-page-scripts.json"
SECRET = re.compile(r"\$\{\{\s*secrets\.")
INTEGRITY = re.compile(r"^sha384-[A-Za-z0-9+/]{64}$")


def check_job() -> dict[str, Any]:
    return dict(workflow(NAME)["jobs"]["check"])


def step_named(job: dict[str, Any], name: str) -> dict[str, Any]:
    [found] = [step for step in steps(job) if step.get("name") == name]
    return found


def test_it_runs_weekly_and_by_hand_with_least_privilege_and_no_secret() -> None:
    document = workflow(NAME)
    on = triggers(document)

    assert on["schedule"] == [{"cron": "23 5 * * 1"}]
    assert "workflow_dispatch" in on
    assert set(on) == {"schedule", "workflow_dispatch"}
    assert document["permissions"] == {"contents": "read"}
    assert "permissions" not in check_job()
    assert document["jobs"]["report"]["permissions"] == {"issues": "write"}
    assert not SECRET.search((ROOT / ".github" / "workflows" / NAME).read_text("utf-8"))
    # Pinned to commits (uses() asserts the pin).
    assert len(uses(check_job(), "actions/checkout")) == 1
    assert len(uses(check_job(), "actions/setup-node")) == 1


def test_it_compares_production_or_a_fresh_build_with_the_inventory() -> None:
    job = check_job()
    compare = step_named(job, "Compare the scripts with the inventory")
    run = str(compare["run"])

    assert job["env"]["PRODUCTION_CABINET_URL"] == "${{ vars.PRODUCTION_CABINET_URL }}"
    assert job["defaults"]["run"]["working-directory"] == "web"
    assert "node scripts/payment-page-integrity.mjs" in run
    assert "--inventory payment-page-scripts.json" in run
    assert '--origin "$PRODUCTION_CABINET_URL"' in run
    assert "--build .next" in run
    assert 'exit "$status"' in run and "GITHUB_STEP_SUMMARY" in run
    for name in ("Install dependencies", "Build"):
        assert step_named(job, name)["if"] == "env.PRODUCTION_CABINET_URL == ''"
    assert "npm run build" in scripts(job)
    keep = step_named(job, "Keep the scripts found")
    assert keep["if"] == "failure() && env.PRODUCTION_CABINET_URL == ''"


def test_a_scheduled_difference_opens_one_issue() -> None:
    report = workflow(NAME)["jobs"]["report"]
    run = scripts(report)

    assert report["needs"] == "check"
    assert report["if"] == "failure() && github.event_name == 'schedule'"
    assert 'title="Payment page scripts changed"' in run
    assert "gh issue comment" in run and "gh issue create" in run


def test_the_inventory_lists_first_party_scripts_of_every_payment_page() -> None:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))

    assert set(inventory["pages"]) == {"/b/[businessId]/settings/billing", "/c/[slug]"}
    for route, page_scripts in inventory["pages"].items():
        assert page_scripts, route
        for script in page_scripts:
            assert re.fullmatch(r"static/chunks/[A-Za-z0-9._-]+\.js", script["path"])
            assert INTEGRITY.match(script["integrity"]), script


def test_the_schedule_watch_notices_when_it_stops() -> None:
    watch = workflow("schedule-watch.yml")["jobs"]["watch"]

    assert NAME in str(steps(watch)[0]["env"]["WATCHED"]).split()
