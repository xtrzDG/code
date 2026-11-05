"""Steps of the referral API tests: owners who sign up by a link, partners."""

from dataclasses import dataclass
from typing import Any

from app.schemas.constants.referrals import CommissionStatus
from app.schemas.domain.referrals import CommissionEntryDocument
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.billing.prefixed_id import InvoiceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.referrals.constrained_integers import (
    CommissionRateBasisPoints,
)
from app.schemas.typings.referrals.constrained_strings import CommissionMonth
from app.schemas.typings.referrals.prefixed_id import PartnerId
from app.utilities.referrals.referral_identity import commission_entry_id
from tests.e2e.harness import Workshop, bearer
from tests.e2e.harness_settings import ADMIN_EMAIL

CABINET_BASE_URL: str = "https://app.workshop.example"
PARTNER_PHONE: str = "+995 599 00 01 11"

type JsonObject = dict[str, Any]


@dataclass(frozen=True)
class Owner:
    headers: dict[str, str]
    user_id: str
    business_id: str

    @property
    def base(self) -> str:
        return f"/v1/businesses/{self.business_id}"


def sign_up(
    workshop: Workshop, phone: str, referral_code: str | None = None
) -> tuple[dict[str, str], str]:
    """Sign in by phone with the `ref` code the cabinet's cookie kept."""

    started = workshop.client.post("/v1/auth/otp/start", json={"phone_number": phone})
    assert started.status_code == 200, started.text
    body: JsonObject = {
        "challenge_id": started.json()["challenge_id"],
        "code": str(workshop.otp.codes[-1].code),
    }
    if referral_code is not None:
        body["signup_attribution"] = {
            "referral_code": referral_code,
            "landing_path": "/",
        }
    verified = workshop.client.post("/v1/auth/otp/verify", json=body)
    assert verified.status_code == 200, verified.text
    session: JsonObject = verified.json()
    return bearer(str(session["access_token"])), str(session["user"]["id"])


def open_business(
    workshop: Workshop,
    phone: str,
    referral_code: str | None = None,
    name: str = "Salobie Bia",
    plan_key: str | None = None,
) -> Owner:
    headers, user_id = sign_up(workshop, phone, referral_code)
    details: JsonObject = {"name": name, "niche_key": "restaurant"}
    if plan_key is not None:
        details["plan_key"] = plan_key
    created = workshop.client.post("/v1/businesses", json=details, headers=headers)
    assert created.status_code == 201, created.text
    return Owner(headers, user_id, str(created.json()["id"]))


def program(workshop: Workshop, owner: Owner) -> JsonObject:
    response = workshop.client.get(f"{owner.base}/referrals", headers=owner.headers)
    assert response.status_code == 200, response.text
    body: JsonObject = response.json()
    return body


def admin_headers(workshop: Workshop) -> dict[str, str]:
    token, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
    return bearer(token)


def add_partner(
    workshop: Workshop, admin: dict[str, str], code: str = "agency-tbilisi"
) -> JsonObject:
    created = workshop.client.post(
        "/v1/admin/partners",
        json={
            "name": "Tbilisi Digital",
            "phone_number": PARTNER_PHONE,
            "commission_rate_basis_points": 2000,
            "code": code,
        },
        headers=admin,
    )
    assert created.status_code == 201, created.text
    body: JsonObject = created.json()
    return body


def accrue(
    workshop: Workshop,
    partner_id: str,
    business_id: str,
    month: str,
    amount_minor: int,
) -> None:
    """A commission as a paid invoice of the business would have earned it."""

    container = workshop.container
    invoice_id = InvoiceId()
    now = workshop.clock.wall_clock.now_unix()
    with container.utilities.storage_scope().platform_wide():
        container.repositories.commission_entry_repo().record(
            CommissionEntryDocument(
                id=commission_entry_id(invoice_id),
                partner_id=PartnerId(partner_id),
                business_id=BusinessId(business_id),
                invoice_id=invoice_id,
                base_minor=MoneyAmountMinor(amount_minor * 5),
                rate_basis_points=CommissionRateBasisPoints(2000),
                amount_minor=MoneyAmountMinor(amount_minor),
                currency_code=CurrencyCode("GEL"),
                accrued_at=now,
                month=CommissionMonth(month),
                status=CommissionStatus.ACCRUED,
            )
        )
