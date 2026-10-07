"""
The cabinet's lists of bookings, requests and handoffs record the address
they were opened from, and opening one again soon only counts the view.
"""

from app.schemas.constants.compliance import AuditAction
from tests.e2e.harness import Workshop
from tests.e2e.journeys import open_restaurant


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
    assert all(int(entry.record_count or 0) == 2 for entry in entries)
