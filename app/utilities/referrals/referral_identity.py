"""
The derived ids and codes of the referral program: a code's id from the
code in lower case, a referral's from the referred business, a commission's
from its invoice, a reward's from the referred business and the side, and a
business's own code from the business.

The namespaces are fixed: stored ids depend on them, never change them.
"""

import base64
import hashlib
from enum import StrEnum
from uuid import UUID, uuid5

from app.schemas.typings.analytics.constrained_strings import ReferralCode
from app.schemas.typings.billing.prefixed_id import BillingCreditId, InvoiceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.referrals.prefixed_id import (
    CommissionEntryId,
    PartnerId,
    ReferralCodeId,
    ReferralId,
)

REFERRAL_CODE_NAMESPACE: UUID = UUID("5b0c8f8e-6a40-4b8e-9a52-1f3c7d2e9b41")
REFERRAL_NAMESPACE: UUID = UUID("b7a51e2c-0d3f-4e9a-8c61-2a4f6e8d1c07")
COMMISSION_NAMESPACE: UUID = UUID("e3d9c1a8-7f24-4b6d-a0e5-9c2b8f4a6d13")
REWARD_NAMESPACE: UUID = UUID("2f6a8c4e-1b3d-4a5f-9e7c-8d0b2a4c6e19")
PARTNER_NAMESPACE: UUID = UUID("9c4e2a6f-8b1d-4f3a-a5c7-0e2d4b6f8a31")
# A business's code: the first characters of a hash of its id, in the
# letters and digits base32 uses (no 0/1/8/9 to misread), lower case. The
# longer one is the fallback should the shorter ever be taken.
BUSINESS_CODE_LENGTHS: tuple[int, ...] = (10, 16)


class RewardSide(StrEnum):
    """Which business a referral reward credits."""

    REFERRED = "referred"
    REFERRER = "referrer"


def normalized_code(code: ReferralCode) -> str:
    """A code as compared: lower case (links are typed and shared by hand)."""

    return str(code).lower()


def referral_code_id(code: ReferralCode) -> ReferralCodeId:
    return ReferralCodeId(uuid5(REFERRAL_CODE_NAMESPACE, normalized_code(code)))


def referral_id(referred_business_id: BusinessId) -> ReferralId:
    return ReferralId(uuid5(REFERRAL_NAMESPACE, str(referred_business_id)))


def commission_entry_id(invoice_id: InvoiceId) -> CommissionEntryId:
    return CommissionEntryId(uuid5(COMMISSION_NAMESPACE, str(invoice_id)))


def reward_credit_id(referred_business_id: BusinessId, side: RewardSide) -> BillingCreditId:
    return BillingCreditId(
        uuid5(REWARD_NAMESPACE, f"{referred_business_id}|{side.value}")
    )


def partner_id_for(destination: str) -> PartnerId:
    """A partner's id from its sign-in destination ("email:…" or "phone:…")."""

    return PartnerId(uuid5(PARTNER_NAMESPACE, destination.lower()))


def business_code_candidates(business_id: BusinessId) -> list[ReferralCode]:
    """The codes a business may own, in the order they are tried."""

    digest: bytes = hashlib.sha256(f"referral|{business_id}".encode()).digest()
    text: str = base64.b32encode(digest).decode("ascii").lower().rstrip("=")
    return [ReferralCode(text[:length]) for length in BUSINESS_CODE_LENGTHS]
