"""
Upcasters of the stored conversations (`document_upgrades` registers them).

Version 6 says who rated a conversation (`rating_by`). Before it only the
owner or staff could rate one in the cabinet, so a version 5 row with a
rating was rated by the team.
"""

# Stored JSON of one document, before validation (the storage boundary).
type StoredJsonObject = dict[str, object]

RATING_FIELD_NAME: str = "rating"
RATING_BY_FIELD_NAME: str = "rating_by"
TEAM_RATING: str = "team"


def upgrade_conversations_from_v5(document: StoredJsonObject) -> StoredJsonObject:
    """A rated version 5 conversation was rated by the team."""

    if document.get(RATING_FIELD_NAME) is None or RATING_BY_FIELD_NAME in document:
        return document

    upgraded: StoredJsonObject = dict(document)
    upgraded[RATING_BY_FIELD_NAME] = TEAM_RATING
    return upgraded
