"""
Meta's self-serve connection in the authorization matrix: the bodies of
the sign-in, signup, page-picker and comment-reply calls (their state is
one no owner started, so they stop at a refusal) and the operations only
owners may call (staff may read whether Facebook sign-in is offered).
"""

from typing import Any

type JsonObject = dict[str, Any]

B: str = "/v1/businesses/{business_id}"
UNSTARTED_STATE: str = "a" * 43
META_BODIES: dict[str, JsonObject] = {
    f"POST {B}/channels/meta/sign-in": {"purpose": "pages"},
    f"POST {B}/channels/whatsapp/embedded-signup": {
        "state": UNSTARTED_STATE,
        "code": "AQB-test-code-0000-0000",
    },
    f"POST {B}/channels/meta/pages": {
        "state": UNSTARTED_STATE,
        "code": "AQD-test-code-0000-0000",
    },
    f"PUT {B}/channels/{{channel}}/page": {
        "state": UNSTARTED_STATE,
        "page_id": "4410001",
    },
    f"PUT {B}/channels/instagram/comment-replies": {"is_on": False},
}
OWNER_ONLY_META_OPERATIONS: frozenset[str] = frozenset(
    {
        f"POST {B}/channels/meta/sign-in",
        f"POST {B}/channels/whatsapp/embedded-signup",
        f"POST {B}/channels/meta/pages",
        f"PUT {B}/channels/{{channel}}/page",
        f"PUT {B}/channels/instagram/comment-replies",
    }
)
