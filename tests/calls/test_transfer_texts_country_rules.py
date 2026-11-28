"""
Settings → Calls words the staff number rule by the business's country:
"another EU country" only to a business in the EU, because calls are put
through only to numbers of the business's own country or of an EU member
state (`find_transfer_refusal`). The cabinet keeps its own copy of the
member states (web/src/app/b/[businessId]/settings/_lib/transferTexts.ts),
so the card never words a rule the API does not apply.
"""

import re
from pathlib import Path

from app.utilities.channels.transfer_destinations import EU_COUNTRY_CODES

CABINET_TRANSFER_TEXTS: Path = (
    Path(__file__).resolve().parents[2]
    / "web/src/app/b/[businessId]/settings/_lib/transferTexts.ts"
)
EU_LIST: re.Pattern[str] = re.compile(
    r"EU_COUNTRY_CODES: ReadonlySet<string> = new Set\(\[(?P<codes>[^\]]*)\]\)"
)
COUNTRY_CODE: re.Pattern[str] = re.compile(r'"([A-Z]{2})"')


def cabinet_eu_country_codes() -> set[str]:
    source: str = CABINET_TRANSFER_TEXTS.read_text(encoding="utf-8")
    found: re.Match[str] | None = EU_LIST.search(source)
    assert found is not None, "transferTexts.ts has no EU_COUNTRY_CODES"
    return set(COUNTRY_CODE.findall(found.group("codes")))


def test_the_cabinet_names_the_member_states_the_transfer_rule_allows() -> None:
    assert cabinet_eu_country_codes() == {str(code) for code in EU_COUNTRY_CODES}
