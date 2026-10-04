"""
Upcasters of the stored knowledge items (`document_upgrades` registers them).

Version 2 limits `duration_minutes` to what one booking of a service can
last (`ServiceDurationMinutes`: 5 to 720 minutes). Version 1 accepted any
length from 1 minute to 30 days (a room type once carried 1440), so such a
duration moves to an attribute of the same name: the assistant still reads
it in the facts, and nothing is booked by it.
"""

from app.schemas.typings.knowledge.constrained_integers import ServiceDurationMinutes

DURATION_FIELD_NAME: str = "duration_minutes"
ATTRIBUTES_FIELD_NAME: str = "attributes"

# Stored JSON of one document, before validation (the storage boundary).
type StoredJsonObject = dict[str, object]


def upgrade_knowledge_items_from_v1(document: StoredJsonObject) -> StoredJsonObject:
    """A duration outside 5 to 720 minutes becomes the attribute `duration_minutes`."""

    duration: object = document.get(DURATION_FIELD_NAME)
    if (
        not isinstance(duration, int)
        or isinstance(duration, bool)
        or int(ServiceDurationMinutes.ge) <= duration <= int(ServiceDurationMinutes.le)
    ):
        return document

    upgraded: StoredJsonObject = dict(document)
    upgraded[DURATION_FIELD_NAME] = None
    stored_attributes: object = document.get(ATTRIBUTES_FIELD_NAME)
    attributes: list[object] = (
        list(stored_attributes) if isinstance(stored_attributes, list) else []
    )
    if not any(
        isinstance(attribute, dict) and attribute.get("key") == DURATION_FIELD_NAME
        for attribute in attributes
    ):
        attributes.append({"key": DURATION_FIELD_NAME, "value": str(duration)})

    upgraded[ATTRIBUTES_FIELD_NAME] = attributes
    return upgraded
