"""
Records and tables of business B for the customer operations of the
matrix: a saved segment (the demo saves none), the bodies of the card,
blocking, settings and segment changes, and the owner-only operations.
"""

from typing import Any

from tests.e2e.harness import Workshop

type JsonObject = dict[str, Any]

B: str = "/v1/businesses/{business_id}"
S: str = f"{B}/customer-segments"
SEGMENT_BODY: JsonObject = {"name": "Regulars", "rules": {"min_bookings": 2}}
CUSTOMER_BODIES: dict[str, JsonObject] = {
    f"PATCH {B}/contacts/{{contact_id}}/card": {"add_tags": ["regular"]},
    f"PUT {B}/contacts/{{contact_id}}/blocking": {"is_blocked": False},
    f"PUT {B}/customer-settings": {"staff_sees_phone_numbers": False},
    f"POST {S}": {**SEGMENT_BODY, "name": "Not back in 60 days"},
    f"PUT {S}/{{segment_id}}": SEGMENT_BODY,
    f"POST {S}/preview": {"last_visit_days_ago": 60},
}
CUSTOMER_QUERIES: dict[str, dict[str, str]] = {f"GET {B}/search": {"q": "Nino"}}
# Blocking a customer, the team's phone visibility and the segments (with
# their members and CSV) are the owner's.
OWNER_ONLY_CUSTOMER_OPERATIONS: frozenset[str] = frozenset(
    {
        f"PUT {B}/contacts/{{contact_id}}/blocking",
        f"PUT {B}/customer-settings",
        f"GET {S}",
        f"POST {S}",
        f"POST {S}/preview",
        f"PUT {S}/{{segment_id}}",
        f"DELETE {S}/{{segment_id}}",
        f"GET {S}/{{segment_id}}/members",
        f"GET {S}/{{segment_id}}/export",
    }
)


def customer_path_values(
    workshop: Workshop,
    business_id: str,
    owner_headers: dict[str, str],
) -> dict[str, str]:
    """segment_id: a segment of business B, saved by its owner."""

    response = workshop.client.post(
        f"/v1/businesses/{business_id}/customer-segments",
        json=SEGMENT_BODY,
        headers=owner_headers,
    )
    assert response.status_code == 201, response.text
    return {"segment_id": str(response.json()["id"])}
