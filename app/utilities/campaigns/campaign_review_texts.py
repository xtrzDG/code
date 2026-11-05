"""
What a business's owners hear when its campaign is held for the platform
team's review and when it is released (ABUSE-05): owner catalog texts
(`campaigns.review_hold.*`) where `{business}`, `{sent}` and `{opted_out}`
are filled in (`fill_hold_notice`).
"""

from app.schemas.domain.campaigns import CampaignReviewHold
from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.owner_texts import owner_text

OWNER_HOLD_NOTICE: LocalizedText = owner_text("campaigns.review_hold.held")
OWNER_RELEASE_NOTICE: LocalizedText = owner_text("campaigns.review_hold.released")


def fill_hold_notice(text: str, business_name: str, hold: CampaignReviewHold) -> str:
    return text.format(
        business=business_name, sent=int(hold.sent), opted_out=int(hold.opted_out)
    )
