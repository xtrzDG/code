"""
SEED_DEMO_DATA: the paid Berlin salon has its billing details filled in, and
its paid invoice carries a number, the card it was paid with and a receipt
the owner downloads as a PDF.
"""

from typing import Any

from tests.demo.test_demo_seeding import (
    DEMO_ENVIRONMENT,
    SALON,
    businesses_by_name,
    sign_in_owner,
)
from tests.e2e.harness import start_workshop

type JsonObject = dict[str, Any]


def test_the_demo_salon_has_billing_details_and_a_numbered_paid_invoice() -> None:
    workshop = start_workshop(DEMO_ENVIRONMENT)
    with workshop.client as client:
        headers = sign_in_owner(workshop)
        salon = businesses_by_name(client, headers)[SALON]
        base = f"/v1/businesses/{salon['id']}/billing"
        profile: JsonObject = client.get(f"{base}/profile", headers=headers).json()
        billing: JsonObject = client.get(base, headers=headers).json()
        invoice: JsonObject = billing["invoices"][0]
        receipt = client.get(
            f"{base}/invoices/{invoice['id']}/documents/receipt?language=en",
            headers=headers,
        )

    assert profile["is_saved"] is True
    assert (profile["legal_name"], profile["country_code"]) == (
        "Studio Lindenblatt GmbH",
        "DE",
    )
    assert billing["subscription"]["status"] == "active"
    assert invoice["status"] == "paid"
    assert str(invoice["number"]).startswith("AW-")
    assert invoice["is_receipt_available"] is True
    assert invoice["paid_at"] is not None
    assert receipt.status_code == 200, receipt.text
    assert receipt.headers["content-type"] == "application/pdf"
    assert receipt.content.startswith(b"%PDF")
