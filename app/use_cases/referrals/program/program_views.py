"""The parts of an owner's invitation view."""

from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.referrals.program import PoweredByView
from app.schemas.typings.referrals.constrained_strings import ReferralLink
from app.utilities.referrals.referral_links import can_hide_powered_by


def build_powered_by_view(
    business: BusinessDocument, link: ReferralLink | None
) -> PoweredByView:
    """The link's state: shown unless a Plus owner hid it, and the link."""

    return PoweredByView(
        is_shown=link is not None,
        is_removable=can_hide_powered_by(business),
        is_hidden=business.hides_powered_by,
        url=link,
    )
