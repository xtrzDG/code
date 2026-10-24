"""
The cabinet's lists of bookings, requests and handoffs record the address
they were opened from, and opening one again soon only counts the view.
"""

from app.schemas.constants.compliance import AuditAction
from tests.e2e.harness import Workshop
from tests.e2e.journeys import open_restaurant


def workspace_views(
    workshop: Workshop, base: str, headers: dict[str, str]
) -> dict[str, int]:
    """The owner's audit log: how many views each list entry stands for."""

    page = workshop.client.get(
        f"{base}/audit-log", params={"action": "view"}, headers=headers
    )
    assert page.status_code == 200, page.text
    return {
        str(item["entity"]): int(item["record_count"])
        for item in page.json()["items"]
        if item["entity"] in {"booking", "lead", "handoff"}
    }


def test_lists_record_the_address_they_were_opened_from(workshop: Workshop) -> None:
    restaurant = open_restaurant(workshop)
    for path in ("bookings", "leads", "handoffs"):
        for _ in range(2):
            response = workshop.client.get(
                f"{restaurant.base}/{path}", headers=restaurant.headers
            )
            assert response.status_code == 200, response.text

    audit_log = workshop.container.adapters.collections.audit_log_entry_collection()
    entries = [
        entry
        for entry in audit_log.list_all()
        if entry.action is AuditAction.VIEW
        and str(entry.entity) in {"booking", "lead", "handoff"}
    ]
    assert sorted(str(entry.entity) for entry in entries) == [
        "booking",
        "handoff",
        "lead",
    ]
    assert all(entry.ip_address is not None for entry in entries)
    # The second look is counted beside the entry, which never changes.
    listed = workspace_views(workshop, restaurant.base, restaurant.headers)
    assert listed == {"booking": 2, "handoff": 2, "lead": 2}
