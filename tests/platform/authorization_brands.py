"""
The routes a location has with its brand, in the business authorization
matrix: replacing a shared fact (owners and staff; its body) and leaving
the brand (owners only). The brand routes themselves (/v1/brands/…) have
their own matrix (tests/platform/test_brand_authorization_matrix.py).
"""

from typing import Any

type JsonObject = dict[str, Any]

B: str = "/v1/businesses/{business_id}"
BRAND_BODIES: dict[str, JsonObject] = {
    f"POST {B}/knowledge/brand-overrides": {"shared_key": "parking"},
}
OWNER_ONLY_BRAND_OPERATIONS: frozenset[str] = frozenset({f"DELETE {B}/brand"})
