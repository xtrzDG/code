"""
The hosted chat's privacy notice names the retention periods the owner
chose in Settings → Privacy (over HTTP, the whole application).
"""

from tests.e2e.harness import Workshop
from tests.sharing.sharing_steps import add_staff, create_business, share_links

OWNER_PHONE: str = "+995 555 11 22 33"
STAFF_PHONE: str = "+995 555 77 88 99"


def test_the_public_chat_names_the_periods_the_owner_chose(workshop: Workshop) -> None:
    business = create_business(workshop, OWNER_PHONE, "Cafe Batumi")
    slug = share_links(workshop, business)["slug"]

    defaults = workshop.client.get(
        f"{business.base}/privacy-settings", headers=business.owner
    )
    changed = workshop.client.put(
        f"{business.base}/privacy-settings",
        json={"conversation_retention_days": 365, "llm_turn_retention_days": 14},
        headers=business.owner,
    )
    public = workshop.client.get(f"/v1/public/chat/{slug}").json()

    assert defaults.status_code == 200
    assert defaults.json()["conversation_retention_days"] == 730
    assert defaults.json()["last_purge"] is None
    assert changed.status_code == 200, changed.text
    assert changed.json()["conversation_retention_days"] == 365
    assert (
        public["conversation_retention_days"],
        public["llm_turn_retention_days"],
    ) == (
        365,
        14,
    )


def test_periods_beyond_the_promises_and_staff_are_refused(workshop: Workshop) -> None:
    business = create_business(workshop, OWNER_PHONE, "Cafe Batumi")
    staff = add_staff(workshop, business, STAFF_PHONE)

    too_short = workshop.client.put(
        f"{business.base}/privacy-settings",
        json={"conversation_retention_days": 7, "llm_turn_retention_days": 30},
        headers=business.owner,
    )
    too_long_for_the_model = workshop.client.put(
        f"{business.base}/privacy-settings",
        json={"conversation_retention_days": 730, "llm_turn_retention_days": 90},
        headers=business.owner,
    )
    by_staff = workshop.client.get(f"{business.base}/privacy-settings", headers=staff)

    assert too_short.status_code == 422
    assert too_long_for_the_model.status_code == 422
    assert by_staff.status_code == 403
