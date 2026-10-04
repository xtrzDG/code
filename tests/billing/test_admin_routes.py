"""The platform admin routes over HTTP: who may use them and what they show."""

from app.schemas.constants.compliance import AuditAction
from tests.billing.billing_testbed import bearer
from tests.billing.route_world import RouteWorld

REASON_BODY: dict[str, str] = {"reason": "Owner asked about the invoice"}


def test_admin_routes() -> None:
    world = RouteWorld()
    world.start_trial()
    detail_path = f"/v1/admin/clients/{world.business.id}"

    listing = world.client.get("/v1/admin/clients", headers=bearer(world.admin))
    detail = world.client.get(detail_path, headers=bearer(world.admin))
    opened = world.client.post(
        f"{detail_path}/open", headers=bearer(world.admin), json=REASON_BODY
    )
    without_reason = world.client.post(
        f"{detail_path}/open", headers=bearer(world.admin)
    )

    filtered = world.client.get(
        "/v1/admin/clients",
        headers=bearer(world.admin),
        params={"health": "critical", "sort": "name", "country": "ge", "limit": "5"},
    )
    invalid = {
        name: world.client.get(
            "/v1/admin/clients", headers=bearer(world.admin), params=params
        ).status_code
        for name, params in {
            "sort": {"sort": "loudest"},
            "health": {"health": "fine"},
            "status": {"status": "sleeping"},
            "country": {"country": "Georgia"},
            "niche": {"niche": "spaceship"},
            "limit": {"limit": "0"},
        }.items()
    }

    assert listing.status_code == 200
    assert listing.json()["totals"]["client_count"] == 1
    assert listing.json()["items"][0]["health_issues"] == ["not_published"]
    assert filtered.status_code == 200
    assert filtered.json()["items"] == []
    assert filtered.json()["matching_count"] == 0
    assert invalid == {
        "sort": 422,
        "health": 422,
        "status": 422,
        "country": 422,
        "niche": 422,
        "limit": 422,
    }
    assert detail.status_code == 200
    assert detail.json()["summary"]["subscription_status"] == "trialing"
    assert opened.status_code == 200
    assert "billing" in opened.json()["sections"]
    assert opened.json()["can_write"] is False
    assert without_reason.status_code == 422
    [entry] = world.testbed.audit_log_repo.list_by_business(world.business.id)
    assert entry.action is AuditAction.SUPPORT_ACCESS_START
    assert str(entry.ip_address) == "testclient"


def test_admin_routes_refuse_everyone_else() -> None:
    world = RouteWorld()

    assert world.client.get("/v1/admin/clients").status_code == 401
    assert (
        world.client.get("/v1/admin/clients", headers=bearer(world.owner)).status_code
        == 403
    )
    assert (
        world.client.post(
            f"/v1/admin/clients/{world.business.id}/open",
            headers=bearer(world.owner),
            json=REASON_BODY,
        ).status_code
        == 403
    )
    assert (
        world.client.get(
            "/v1/admin/clients/business_nope",
            headers=bearer(world.admin),
        ).status_code
        == 404
    )
    assert world.testbed.audit_log_repo.list_by_business(world.business.id) == []
