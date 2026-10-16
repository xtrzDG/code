"""
Upcasters of the stored contacts (`document_upgrades` registers them).

Version 3 adds the customer list's lookups: `display_name_folded`, the
name as the search compares it, and `last_seen_at`, the latest activity.
A version 2 row gets its folded name and, unless only the owner's test
chat or the autotests made it, its creation as its last activity (the
best the row itself knows; the next message moves it on).
`workshop migrate-documents --collection contacts` writes them, and the
trigger of migration 1122 copies them into their lookup columns.
"""

from typing import cast

from app.schemas.constants.channels import ChannelKind
from app.utilities.contacts.contact_search import fold_contact_name

# Stored JSON of one document, before validation (the storage boundary).
type StoredJsonObject = dict[str, object]


def upgrade_contacts_from_v2(document: StoredJsonObject) -> StoredJsonObject:
    upgraded: StoredJsonObject = dict(document)
    name: object = document.get("name")
    folded = fold_contact_name(name if isinstance(name, str) else None)
    upgraded["display_name_folded"] = None if folded is None else str(folded)
    if upgraded.get("last_seen_at") is None and not is_test_only(document):
        upgraded["last_seen_at"] = document.get("created_at")

    return upgraded


def is_test_only(document: StoredJsonObject) -> bool:
    identities: object = document.get("channel_identities")
    if not isinstance(identities, list) or not identities:
        return False

    return all(
        isinstance(identity, dict)
        and cast(dict[str, object], identity).get("channel")
        == ChannelKind.OWNER_TEST.value
        for identity in cast(list[object], identities)
    )
