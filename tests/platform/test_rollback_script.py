"""
The one-command rollback (scripts/rollback.py, REL-08): it rolls back
every service of render.yaml that deploys `release`, the API first, the
cabinet after the workers and the backup cron last, to the last live deploy
of the good commit; without --apply
it only plans, a service without such a deploy stops it before anything
changes, and a refusal stops it at once.
"""

import io
import json

import httpx

from scripts.rollback import (
    EXIT_FAILED,
    EXIT_OK,
    EXIT_USAGE,
    ROLLBACK_ORDER,
    release_services,
    run,
)

GOOD: str = "a" * 40
BAD: str = "b" * 40
SERVICES: list[str] = ["workshop-api", "workshop-worker", "workshop-cabinet"]


class FakeRender:
    """Render's API for three services, each with a deploy of GOOD and BAD."""

    def __init__(self, refuse: str | None = None, missing: str | None = None) -> None:
        self.rollbacks: list[tuple[str, str]] = []
        self.refuse = refuse
        self.missing = missing

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer key"
        path = request.url.path.removeprefix("/v1")
        if path == "/services":
            name = request.url.params["name"]
            return httpx.Response(
                200, json=[{"service": {"id": f"srv-{name}", "name": name}}]
            )
        service = path.split("/")[2].removeprefix("srv-")
        if path.endswith("/deploys"):
            deploys = [
                {
                    "deploy": {
                        "id": f"dep-bad-{service}",
                        "status": "live",
                        "commit": {"id": BAD},
                    }
                }
            ]
            if service != self.missing:
                deploys.append(
                    {
                        "deploy": {
                            "id": f"dep-good-{service}",
                            "status": "deactivated",
                            "commit": {"id": GOOD},
                        }
                    }
                )
            return httpx.Response(200, json=deploys)
        assert path.endswith("/rollback") and request.method == "POST"
        if service == self.refuse:
            return httpx.Response(409, json={"message": "busy"})
        self.rollbacks.append((service, json.loads(request.content)["deployId"]))
        return httpx.Response(201, json={})


def call(arguments: list[str], render: FakeRender, key: str = "key") -> tuple[int, str]:
    output = io.StringIO()
    code = run(
        arguments,
        {"RENDER_API_KEY": key},
        output,
        transport=httpx.MockTransport(render.handle),
        services=SERVICES,
    )
    return code, output.getvalue()


def test_every_service_of_release_is_rolled_back_in_the_runbooks_order() -> None:
    services = release_services()

    assert set(services) == set(ROLLBACK_ORDER)
    assert services[0] == "workshop-api"
    # The cabinet follows the API and the workers; the backup cron, which no
    # customer reaches, comes last, so its refusal leaves nobody on the bad
    # commit.
    assert services.index("workshop-cabinet") > services.index("workshop-worker")
    assert services.index("workshop-cabinet") > services.index("workshop-batch-worker")
    assert services[-1] == "workshop-backup"


def test_without_apply_it_only_plans() -> None:
    render = FakeRender()

    code, text = call([GOOD], render)

    assert code == EXIT_OK
    assert render.rollbacks == []
    assert "workshop-api (srv-workshop-api): dep-good-workshop-api" in text
    assert "--apply" in text


def test_apply_rolls_back_each_service_to_the_good_deploy_then_names_step_2() -> None:
    render = FakeRender()

    code, text = call([GOOD, "--apply"], render)

    assert code == EXIT_OK
    assert render.rollbacks == [(name, f"dep-good-{name}") for name in SERVICES]
    assert f"git push --force-with-lease origin {GOOD}:release" in text


def test_a_service_without_a_deploy_of_the_commit_stops_everything() -> None:
    render = FakeRender(missing="workshop-cabinet")

    code, text = call([GOOD, "--apply"], render)

    assert code == EXIT_FAILED
    assert render.rollbacks == []
    assert "NO DEPLOY OF THIS COMMIT" in text


def test_a_refusal_stops_at_that_service() -> None:
    render = FakeRender(refuse="workshop-worker")

    code, text = call([GOOD, "--apply"], render)

    assert code == EXIT_FAILED
    assert render.rollbacks == [("workshop-api", "dep-good-workshop-api")]
    assert "refused the rollback of workshop-worker (409)" in text


def test_wrong_arguments_or_no_key_change_nothing() -> None:
    render = FakeRender()

    assert call([], render)[0] == EXIT_USAGE
    assert call(["abc123"], render)[0] == EXIT_USAGE
    assert call([GOOD], render, key="")[0] == EXIT_USAGE
    assert render.rollbacks == []
