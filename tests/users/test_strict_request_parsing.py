from app.gateways.http.strict_request_parsing import inline_local_references

ADDRESS_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {"city": {"type": "string"}},
}
CONTACT_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {"address": ADDRESS_SCHEMA},
}


def test_local_references_are_inlined_and_other_references_kept() -> None:
    definitions: dict[str, object] = {
        "Address": ADDRESS_SCHEMA,
        "Contact": {
            "type": "object",
            "properties": {"address": {"$ref": "#/$defs/Address"}},
        },
    }
    schema: dict[str, object] = {
        "properties": {
            "contacts": {"type": "array", "items": {"$ref": "#/$defs/Contact"}},
            "primary": {"$ref": "#/$defs/Contact", "description": "Main contact"},
            "external": {"$ref": "https://example.com/schema.json"},
        }
    }

    assert inline_local_references(schema, definitions) == {
        "properties": {
            "contacts": {"type": "array", "items": CONTACT_SCHEMA},
            "primary": CONTACT_SCHEMA | {"description": "Main contact"},
            "external": {"$ref": "https://example.com/schema.json"},
        }
    }
