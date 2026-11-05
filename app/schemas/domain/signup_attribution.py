from base_pydantic_schemas import PersistentDocument
from typed_time_provider import Microseconds

from app.schemas.typings.analytics.constrained_strings import (
    LandingPath,
    ReferralCode,
    ReferrerHost,
    SignupSourceTag,
    UtmCampaign,
    UtmContent,
    UtmMedium,
    UtmSource,
    UtmTerm,
)


class SignupAttribution(PersistentDocument):
    """
    Where a new owner came from, as the cabinet saw it on their first visit
    to the landing or a hosted chat page (the first-party `aw_attr` cookie):
    the campaign of the link (utm_*), its `ref` code and `src` tag, the
    site they came from (host only) and the first page they opened. Kept on
    the user once, at sign-up; it names no other person.
    """

    utm_source: UtmSource | None = None
    utm_medium: UtmMedium | None = None
    utm_campaign: UtmCampaign | None = None
    utm_term: UtmTerm | None = None
    utm_content: UtmContent | None = None
    referral_code: ReferralCode | None = None
    source_tag: SignupSourceTag | None = None
    referrer_host: ReferrerHost | None = None
    landing_path: LandingPath | None = None
    first_seen_at: Microseconds | None = None
