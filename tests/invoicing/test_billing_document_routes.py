"""
The billing details and invoice PDF routes: owners only, the details
validated at the boundary, the PDF a download with its number for a name.
"""

from fastapi.testclient import TestClient

from app.schemas.constants.compliance import AuditAction
from tests.billing.billing_testbed import bearer
from tests.billing.paid_world import PaidWorld, checkout
from tests.invoicing.document_world import HtmlEchoRenderer, build_document_world
from tests.invoicing.invoicing_world import build_seller_trial

DETAILS: dict[str, object] = {
    "legal_name": "Mtsvane Ezo LLC",
    "tax_id": "405123456",
    "address": "12 Rustaveli Ave\n0108 Tbilisi",
    "billing_email": "accounts@mtsvane-ezo.ge",
    "country_code": "GE",
}


def client_of(world: PaidWorld) -> TestClient:
    return build_document_world(world, HtmlEchoRenderer()).http_client()


def profile_path(world: PaidWorld) -> str:
    return f"/v1/businesses/{world.business.id}/billing/profile"


def test_the_details_start_from_the_business_and_save_with_their_vat() -> None:
    world = build_seller_trial(is_vat_registered=True)
    client = client_of(world)
    headers = bearer(world.owner)

    before = client.get(profile_path(world), headers=headers)
    saved = client.put(profile_path(world), json=DETAILS, headers=headers)
    after = client.get(profile_path(world), headers=headers)

    assert before.status_code == 200
    assert before.json() == {
        "business_id": str(world.business.id),
        "is_saved": False,
        "legal_name": "Mtsvane Ezo",
        "tax_id": None,
        "address": None,
        "billing_email": None,
        "country_code": "GE",
        "tax_treatment": "standard",
        "tax_rate_basis_points": 1800,
    }
    assert saved.status_code == 200
    assert after.json() == {
        **DETAILS,
        "business_id": str(world.business.id),
        "is_saved": True,
        "tax_treatment": "standard",
        "tax_rate_basis_points": 1800,
    }
    entry = world.testbed.audit_log_repo.list_by_business(world.business.id)[-1]
    assert (entry.action, str(entry.entity)) == (AuditAction.UPDATE, "billing_profile")


def test_a_business_abroad_with_a_tax_number_is_reverse_charged() -> None:
    world = build_seller_trial(is_vat_registered=True)

    response = client_of(world).put(
        profile_path(world),
        json={**DETAILS, "country_code": "DE", "tax_id": "DE123456789"},
        headers=bearer(world.owner),
    )

    assert response.json()["tax_treatment"] == "reverse_charge"
    assert response.json()["tax_rate_basis_points"] == 0


def test_details_are_checked_at_the_boundary() -> None:
    world = build_seller_trial(is_vat_registered=False)
    client = client_of(world)
    headers = bearer(world.owner)

    for body in (
        {**DETAILS, "country_code": "ZZ"},
        {**DETAILS, "country_code": "EU"},
        {**DETAILS, "country_code": "AQ"},
        {**DETAILS, "country_code": "Georgia"},
        {**DETAILS, "billing_email": "not-an-address"},
        {**DETAILS, "tax_id": "--"},
        {**DETAILS, "legal_name": ""},
        {"country_code": "GE"},
    ):
        response = client.put(profile_path(world), json=body, headers=headers)

        assert response.status_code == 422, body
    assert (
        world.testbed.invoicing.billing_profile_repo.get_by_business(world.business.id)
        is None
    )


def test_billing_details_and_documents_are_for_owners() -> None:
    world = build_seller_trial(is_vat_registered=False)
    staff = world.testbed.add_user(email="staff@example.com")
    business = world.testbed.business(world.business.id)
    business.members = [
        *business.members,
        business.members[0].model_copy(update={"user_id": staff.id, "role": "staff"}),
    ]
    world.testbed.business_repo.save(business)
    checkout(world)
    invoice = world.testbed.invoices(world.business.id)[0]
    client = client_of(world)
    document = (
        f"/v1/businesses/{world.business.id}/billing/invoices/{invoice.id}"
        "/documents/invoice"
    )

    assert client.get(profile_path(world), headers=bearer(staff)).status_code == 403
    assert client.get(document, headers=bearer(staff)).status_code == 403
    assert client.get(document).status_code == 401


def test_the_invoice_downloads_as_a_pdf_named_after_its_number() -> None:
    world = build_seller_trial(is_vat_registered=False)
    checkout(world)
    invoice = world.testbed.invoices(world.business.id)[0]
    client = client_of(world)
    base = f"/v1/businesses/{world.business.id}/billing/invoices/{invoice.id}/documents"
    headers = bearer(world.owner)

    response = client.get(f"{base}/invoice?language=en", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == (
        'attachment; filename="invoice-AW-2026-000001.pdf"; '
        "filename*=UTF-8''invoice-AW-2026-000001.pdf"
    )
    assert response.headers["cache-control"] == "private, no-store"
    assert "<h1>Invoice</h1>" in response.text
    assert client.get(f"{base}/receipt", headers=headers).status_code == 409
    assert client.get(f"{base}/statement", headers=headers).status_code == 404
    assert client.get(
        f"{base}/invoice?language=xx-!!", headers=headers
    ).status_code == (422)
    other = f"/v1/businesses/{world.business.id}/billing/invoices/invoice_x/documents"
    assert client.get(f"{other}/invoice", headers=headers).status_code in {404, 422}
