"""
The version of the consent wording the booking page sends is the one this
release stores as current, so a stored consent names the text the guest saw.
"""

import re
from pathlib import Path

from app.schemas.constants.marketing_consent import (
    CURRENT_MARKETING_CONSENT_TEXT,
    MarketingConsentText,
)

TEXTS_FILE: Path = (
    Path(__file__).resolve().parents[2]
    / "web/src/app/r/[token]/_components/marketingConsent/consentTexts.ts"
)
VERSION_LINE: re.Pattern[str] = re.compile(
    r'export const MARKETING_CONSENT_TEXT_VERSION = "([0-9-]+)";'
)


def test_the_booking_page_sends_the_current_version_of_the_wording() -> None:
    found = VERSION_LINE.search(TEXTS_FILE.read_text(encoding="utf-8"))

    assert found is not None
    assert MarketingConsentText(found.group(1)) is CURRENT_MARKETING_CONSENT_TEXT
