"""
Upcasters of the stored channels (`document_upgrades` registers them).

Version 4 keeps one WhatsApp staff template per language in
`whatsapp_staff_templates`. A version 3 channel had at most one,
`whatsapp_staff_template`; it becomes the one entry of the list (and stays
where it was, as version 4 still writes it for the previous release).
"""

from typing import cast

SINGLE_TEMPLATE_FIELD_NAME: str = "whatsapp_staff_template"
TEMPLATES_FIELD_NAME: str = "whatsapp_staff_templates"

# Stored JSON of one document, before validation (the storage boundary).
type StoredJsonObject = dict[str, object]


def upgrade_channels_from_v3(document: StoredJsonObject) -> StoredJsonObject:
    """The single staff template of version 3 as a one-template list."""

    single: object = document.get(SINGLE_TEMPLATE_FIELD_NAME)
    stored_list: object = document.get(TEMPLATES_FIELD_NAME)
    has_list: bool = (
        isinstance(stored_list, list) and len(cast(list[object], stored_list)) > 0
    )
    if not isinstance(single, dict) or has_list:
        return document

    upgraded: StoredJsonObject = dict(document)
    upgraded[TEMPLATES_FIELD_NAME] = [dict(cast(StoredJsonObject, single))]
    return upgraded
