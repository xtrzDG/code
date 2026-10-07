"""What the menu model is asked: instructions and the strict JSON schema."""

from app.schemas.constants.knowledge import KnowledgeItemKind

MAX_OUTPUT_TOKENS: int = 32_000
REASONING_EFFORT: str = "low"
MENU_ITEM_KINDS: list[str] = [
    kind.value
    for kind in KnowledgeItemKind
    if kind not in (KnowledgeItemKind.FAQ, KnowledgeItemKind.POLICY)
]
EXTRACTION_INSTRUCTIONS: str = (
    "You read menus and price lists of businesses (restaurants, salons, hotels, "
    "clubs, shops) in any language and return every line a customer can order "
    "or book as one item.\n"
    "- kind: menu_item for food and drinks, service for services, room_type for "
    "rooms, package for packages and sets, vehicle for vehicles, product for "
    "goods.\n"
    "- title: the name exactly as printed, in the printed language.\n"
    "- body: a short description if printed, else null.\n"
    "- price: the printed price as a plain number in major units with a dot "
    "(for example 18.50), else null. Never compute or guess a price.\n"
    "- currency: the ISO 4217 code of the printed currency (₾ is GEL, € is EUR, "
    "₪ is ILS, ֏ is AMD), or null when no currency is printed.\n"
    "- duration_minutes: the printed duration of a service, else null.\n"
    "- tags: up to five short lowercase English tags (vegetarian, spicy, "
    "kids, alcohol), or an empty list.\n"
    "- confidence: from 0 to 1, how sure you are that title and price are "
    "read correctly (blurred or cut text lowers it).\n"
    "Do not invent items. Skip headings, addresses and opening hours."
)
NULLABLE_STRING: dict[str, object] = {"anyOf": [{"type": "string"}, {"type": "null"}]}
MENU_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": MENU_ITEM_KINDS},
                    "title": {"type": "string"},
                    "body": NULLABLE_STRING,
                    "price": NULLABLE_STRING,
                    "currency": NULLABLE_STRING,
                    "duration_minutes": {
                        "anyOf": [{"type": "integer"}, {"type": "null"}]
                    },
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number"},
                },
                "required": [
                    "kind",
                    "title",
                    "body",
                    "price",
                    "currency",
                    "duration_minutes",
                    "tags",
                    "confidence",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}
TEXT_FORMAT: dict[str, object] = {
    "type": "json_schema",
    "name": "menu_items",
    "schema": MENU_SCHEMA,
    "strict": True,
}
