"""
Calls in the authorization matrix, so far the phone line: the bodies of
taking a number and asking the team for one, the operations only owners
may call, and the query a number search needs. Any member reads the phone
card; looking for, taking and asking for numbers is the owner's (they cost
money).
"""

from typing import Any

type JsonObject = dict[str, Any]

B: str = "/v1/businesses/{business_id}"
PHONE_NUMBER_BODIES: dict[str, JsonObject] = {
    f"POST {B}/phone-line/number": {
        "phone_number": "+15125550142",
        "number_type": "local",
        "offer_token": "1767225600.AAAAAAAAAAAAAAAAAAAAAA",
        "monthly_price": {"amount_minor": 500, "currency_code": "GEL"},
    },
    f"POST {B}/phone-line/request": {"country_code": "GE", "number_type": "local"},
}
PHONE_NUMBER_QUERIES: dict[str, dict[str, str]] = {
    f"GET {B}/phone-line/offers": {"country": "US", "number_type": "local"},
}
OWNER_ONLY_PHONE_NUMBER_OPERATIONS: frozenset[str] = frozenset(
    {
        f"GET {B}/phone-line/offers",
        f"POST {B}/phone-line/number",
        f"POST {B}/phone-line/request",
        f"DELETE {B}/phone-line/request",
    }
)
