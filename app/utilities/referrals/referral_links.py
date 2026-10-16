"""
Links that carry a referral code: the platform's own site with `?ref=` (the
code) and `&src=` (where the link was shown). The cabinet's first-touch
cookie keeps both until the visitor signs up.
"""

from urllib.parse import urlencode

from app.schemas.constants.billing import PlanKey
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.analytics.constrained_strings import (
    ReferralCode,
    SignupSourceTag,
)
from app.schemas.typings.referrals.constrained_strings import ReferralLink

# Plans whose owners may leave the "Powered by" link off their chat and card.
POWERED_BY_REMOVABLE_PLANS: frozenset[PlanKey] = frozenset({PlanKey.PLUS})


def build_referral_link(
    site_url: str, code: ReferralCode, source: SignupSourceTag
) -> ReferralLink:
    """The site's front page with the code and the source tag."""

    query: str = urlencode({"ref": str(code), "src": str(source)})
    return ReferralLink(f"{site_url.rstrip('/')}/?{query}")


def can_hide_powered_by(business: BusinessDocument) -> bool:
    """Whether the business's plan lets its owner remove the link."""

    return business.plan_key in POWERED_BY_REMOVABLE_PLANS


def shows_powered_by(business: BusinessDocument) -> bool:
    """
    Whether the chat, the hosted page and the table card carry the link: always,
    unless a Plus owner switched it off (a choice made on Plus stops counting
    when the business leaves Plus).
    """

    return not (business.hides_powered_by and can_hide_powered_by(business))
