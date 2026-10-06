"""Constants of the referral and partner program (migration 1150)."""

from enum import StrEnum

from app.schemas.typings.analytics.constrained_strings import SignupSourceTag


class CommissionStatus(StrEnum):
    """
    A partner's commission on one paid invoice: ACCRUED when the invoice
    was paid, PAID once the platform team paid it out (with the month's
    other commissions of that partner).
    """

    ACCRUED = "accrued"
    PAID = "paid"


class PartnerStatus(StrEnum):
    """
    ACTIVE partners earn commission on every paid invoice of the businesses
    they brought; a PAUSED partner keeps what was earned but earns nothing
    new until resumed (their portal and links keep working).
    """

    ACTIVE = "active"
    PAUSED = "paused"


class ReferralCodeOwnerKind(StrEnum):
    """
    Whose a referral code is: a PARTNER's (commission on every paid invoice
    of the businesses it brings) or a BUSINESS's (an owner inviting another
    owner: a month of credit for both after the first payment).
    """

    PARTNER = "partner"
    BUSINESS = "business"


# Where a referral link was shown: the `src` of its address, so the
# founder's sources table tells an invitation from a chat's footer.
INVITE_SOURCE_TAG: SignupSourceTag = SignupSourceTag("invite")
PARTNER_SOURCE_TAG: SignupSourceTag = SignupSourceTag("partner")
POWERED_BY_SOURCE_TAG: SignupSourceTag = SignupSourceTag("powered_by")
TABLE_CARD_SOURCE_TAG: SignupSourceTag = SignupSourceTag("table_card")
