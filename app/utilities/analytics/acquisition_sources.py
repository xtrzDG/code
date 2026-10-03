"""Where an owner came from, as one normalized key for the founder's reports."""

import re

from app.schemas.domain.signup_attribution import SignupAttribution
from app.schemas.typings.analytics.constrained_strings import AcquisitionSourceKey

UNKNOWN_SOURCE: AcquisitionSourceKey = AcquisitionSourceKey("unknown")
DIRECT_SOURCE: AcquisitionSourceKey = AcquisitionSourceKey("direct")
REFERRAL_SOURCE: AcquisitionSourceKey = AcquisitionSourceKey("referral")
HOSTED_CHAT_SOURCE: AcquisitionSourceKey = AcquisitionSourceKey("hosted_chat")
HOSTED_CHAT_PATH_PREFIX: str = "/c/"
MAX_SOURCE_LENGTH: int = 120
# Anything but the key's own characters becomes a dash.
NOT_KEY_CHARACTERS: re.Pattern[str] = re.compile(r"[^a-z0-9._:-]+")


def acquisition_source_of(
    attribution: SignupAttribution | None,
) -> AcquisitionSourceKey:
    """
    The source of a sign-up, most specific first: the campaign source
    (utm_source), the link's `src` tag, `referral` for a `ref` code,
    `hosted_chat` for a visitor who first opened a business's chat page,
    the referring site, else `direct`; `unknown` for an account without
    attribution (created before it was kept, or the cookie was refused).
    """

    if attribution is None:
        return UNKNOWN_SOURCE

    for candidate in (attribution.utm_source, attribution.source_tag):
        key: AcquisitionSourceKey | None = normalize_source(
            None if candidate is None else str(candidate)
        )
        if key is not None:
            return key

    if attribution.referral_code is not None:
        return REFERRAL_SOURCE

    landing: str = (
        "" if attribution.landing_path is None else str(attribution.landing_path)
    )
    if landing.startswith(HOSTED_CHAT_PATH_PREFIX):
        return HOSTED_CHAT_SOURCE

    if attribution.referrer_host is not None:
        host: str = str(attribution.referrer_host).removeprefix("www.")
        return normalize_source(host) or DIRECT_SOURCE

    return DIRECT_SOURCE


def normalize_source(text: str | None) -> AcquisitionSourceKey | None:
    """Lower case, runs of other characters as one dash; None when empty."""

    if text is None:
        return None

    key: str = NOT_KEY_CHARACTERS.sub("-", text.strip().lower()).strip("-._:")
    if key == "":
        return None

    return AcquisitionSourceKey(key[:MAX_SOURCE_LENGTH].rstrip("-._:"))
