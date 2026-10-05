"""
Settings → Privacy over HTTP: the owner turns the nightly quality sample of
the business's conversations off and on; leaving the switch out of a
request keeps it as it is, and the change is audited.
"""

from app.schemas.constants.compliance import AuditAction
from tests.e2e.harness import Workshop
from tests.sharing.sharing_steps import create_business

OWNER_PHONE: str = "+995 555 11 22 33"
PERIODS: dict[str, int] = {
    "conversation_retention_days": 730,
    "llm_turn_retention_days": 30,
}


def test_the_owner_turns_the_quality_sample_off(workshop: Workshop) -> None:
    business = create_business(workshop, OWNER_PHONE, "Clinic Tbilisi")
    url = f"{business.base}/privacy-settings"

    before = workshop.client.get(url, headers=business.owner).json()
    turned_off = workshop.client.put(
        url,
        json={**PERIODS, "quality_sampling_allowed": False},
        headers=business.owner,
    )
    kept = workshop.client.put(url, json=PERIODS, headers=business.owner)
    turned_on = workshop.client.put(
        url,
        json={**PERIODS, "quality_sampling_allowed": True},
        headers=business.owner,
    )

    assert before["quality_sampling_allowed"] is True
    assert turned_off.status_code == 200, turned_off.text
    assert turned_off.json()["quality_sampling_allowed"] is False
    assert kept.json()["quality_sampling_allowed"] is False
    assert turned_on.json()["quality_sampling_allowed"] is True
    entries = workshop.container.adapters.collections.audit_log_entry_collection()
    updates = [
        entry
        for entry in entries.list_all()
        if entry.action is AuditAction.UPDATE
        and str(entry.entity) == "privacy_settings"
    ]
    assert len(updates) == 3
