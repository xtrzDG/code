"""Version 2 contacts read with the customer list's lookups (version 3, 1122) and on."""

import json

from app.adapters.storage.document_upgrades import (
    CURRENT_SCHEMA_VERSION,
    StoredJsonObject,
    upcasters_of,
    upgrade_stored_json,
)
from app.schemas.domain.contacts import ContactDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName

CONTACTS = DocumentCollectionName("contacts")


def stored_v2(**fields: object) -> StoredJsonObject:
    return {
        "schema_version": "2",
        "business_id": str(BusinessId()),
        "created_at": 1_700_000_000_000_000,
        "updated_at": 1_700_000_000_000_000,
        **fields,
    }


def read(document: StoredJsonObject) -> tuple[StoredJsonObject, ContactDocument]:
    upgraded = upgrade_stored_json(
        document, upcasters_of(CONTACTS), CURRENT_SCHEMA_VERSION[CONTACTS]
    )
    return upgraded, ContactDocument.model_validate_json(json.dumps(upgraded))


def test_a_customer_gets_a_folded_name_and_is_seen_since_creation() -> None:
    upgraded, contact = read(stored_v2(name="  Níno ÄBASHIDZE "))

    assert upgraded["schema_version"] == CURRENT_SCHEMA_VERSION[CONTACTS]
    assert upgraded["last_seen_at"] == 1_700_000_000_000_000
    assert contact.last_seen_at == 1_700_000_000_000_000
    assert contact.display_name_folded is not None
    assert str(contact.display_name_folded) == str(upgraded["display_name_folded"])
    assert str(contact.display_name_folded) == "nino abashidze"


def test_a_contact_without_a_name_has_no_folded_name() -> None:
    upgraded, contact = read(stored_v2())

    assert upgraded["display_name_folded"] is None
    assert contact.display_name_folded is None
    assert contact.last_seen_at == 1_700_000_000_000_000


def test_a_contact_of_the_owner_test_chat_stays_unseen() -> None:
    upgraded, contact = read(
        stored_v2(
            channel_identities=[
                {"channel": "owner_test", "channel_user_id": "owner:1:default"}
            ]
        )
    )

    assert "last_seen_at" not in upgraded
    assert contact.last_seen_at is None
    assert contact.is_test_only


def test_a_later_activity_already_stored_is_kept() -> None:
    upgraded, _ = read(stored_v2(last_seen_at=1_800_000_000_000_000))

    assert upgraded["last_seen_at"] == 1_800_000_000_000_000
