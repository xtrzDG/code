"""
The version of the consent wording the booking page sends is the one this
release stores as current, and the wording this version names is the one
the page and the team's card show, so a stored consent names the text the
customer saw.
"""

import re
from pathlib import Path

from app.schemas.constants.marketing_consent import (
    CURRENT_MARKETING_CONSENT_TEXT,
    MarketingConsentText,
)

WEB: Path = Path(__file__).resolve().parents[2] / "web/src"
TEXTS_FILE: Path = WEB / "app/r/[token]/_components/marketingConsent/consentTexts.ts"
CABINET_TEXTS_FILE: Path = WEB / "i18n/messages/sections/customers/customers.en.ts"
VERSION_LINE: re.Pattern[str] = re.compile(
    r'export const MARKETING_CONSENT_TEXT_VERSION = "([0-9-]+)";'
)
ENGLISH_BOX: re.Pattern[str] = re.compile(
    r'  en: \{\n    label: "([^"]+)",\n    note: "([^"]+)",'
)
CABINET_WORDING: re.Pattern[str] = re.compile(r'    wording: "“([^"]+)”",')


def one_line(text: str) -> str:
    return " ".join(text.split())


def test_the_booking_page_sends_the_current_version_of_the_wording() -> None:
    found = VERSION_LINE.search(TEXTS_FILE.read_text(encoding="utf-8"))

    assert found is not None
    assert MarketingConsentText(found.group(1)) is CURRENT_MARKETING_CONSENT_TEXT


def test_the_version_names_the_wording_the_page_and_the_card_show() -> None:
    box = ENGLISH_BOX.search(TEXTS_FILE.read_text(encoding="utf-8"))
    card = CABINET_WORDING.search(CABINET_TEXTS_FILE.read_text(encoding="utf-8"))
    documented: str = one_line(MarketingConsentText.__doc__ or "")

    assert box is not None and card is not None
    label, note = box.group(1), box.group(2)
    assert card.group(1) == label
    assert f'"{label}"' in documented
    assert f'"{note}"' in documented
