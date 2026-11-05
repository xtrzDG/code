"""
End to end over HTTP: an owner leaving or switching asks for the full
export; the worker writes it and the one-time link downloads a ZIP with
the records, the assistant's versions and instructions, the call and
privacy settings, the rest of the setup, the channels without their
credentials, the consent ledger and the recordings' list, in the archive
format its README names. A receiving provider can validate it: every JSON
file is an array of documents of a stored kind (their recorded schemas).
"""

import io
import json
import zipfile

from base_pydantic_schemas import PersistentDocument

from app.schemas.dto.privacy.archived_recordings import ArchivedRecording
from app.utilities.storage.document_collection_catalog import DOCUMENT_COLLECTIONS
from tests.e2e.harness import Workshop
from tests.e2e.journeys import BUSINESS_BOT_TOKEN, open_restaurant
from tests.e2e.telegram_customer import TelegramCustomer

CONFIGURATION_FILES: frozenset[str] = frozenset(
    {
        "business_profile.json",
        "assistant_versions.json",
        "call_settings.json",
        "privacy_settings.json",
        "channels.json",
        "consent_records.json",
        "recordings.json",
        "schedule_exceptions.json",
        "deposit_settings.json",
        "waitlist_settings.json",
        "campaign_settings.json",
        "review_settings.json",
        "inbox_settings.json",
        "assistant_settings.json",
        "customer_settings.json",
        "customer_segments.json",
        "quick_reply_libraries.json",
        "conversation_notes.json",
    }
)
# Files named apart from the collection whose documents they hold.
COLLECTION_OF_FILE: dict[str, str] = {
    "business": "businesses",
    "audit_log": "audit_log_entries",
    "business_profile": "business_profiles",
    "privacy_settings": "business_privacy_settings",
}
STORED_KINDS: dict[str, type[PersistentDocument]] = {
    str(definition.name): definition.document_type
    for definition in DOCUMENT_COLLECTIONS
}


def downloaded_export(workshop: Workshop) -> dict[str, bytes]:
    """A restaurant with a customer asks for its full export: the files."""

    client = workshop.client
    restaurant = open_restaurant(workshop)
    base, headers = restaurant.base, restaurant.headers
    TelegramCustomer(workshop, restaurant)

    asked = client.post(f"{base}/business-exports", json={}, headers=headers)
    assert asked.status_code in (200, 201, 202), asked.text
    export_id = str(asked.json()["id"])
    workshop.run_queued_jobs()
    link = client.post(
        f"{base}/business-exports/{export_id}/download-link", json={}, headers=headers
    )
    assert link.status_code in (200, 201), link.text
    downloaded = client.get(str(link.json()["download_path"]), headers=headers)
    assert downloaded.status_code == 200, downloaded.text

    with zipfile.ZipFile(io.BytesIO(downloaded.content)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def test_the_full_export_takes_the_setup_along(workshop: Workshop) -> None:
    files = downloaded_export(workshop)

    assert set(files) >= CONFIGURATION_FILES
    assert b"Archive format 2." in files["README.txt"]
    versions = json.loads(files["assistant_versions.json"])
    assert versions and all(version["prompt_text"] for version in versions)
    [channel] = json.loads(files["channels.json"])
    assert channel["kind"] == "telegram"
    assert channel["encrypted_secret"] is None
    assert all(BUSINESS_BOT_TOKEN.encode() not in content for content in files.values())
    assert json.loads(files["recordings.json"]) == []


def test_every_json_file_validates_against_its_stored_kind(
    workshop: Workshop,
) -> None:
    files = downloaded_export(workshop)

    validated: dict[str, int] = {}
    for name, content in files.items():
        if not name.endswith(".json"):
            continue

        # Each element read as the JSON it is, as a receiving system reads it.
        elements: list[str] = [json.dumps(item) for item in json.loads(content)]
        stem = name.removesuffix(".json")
        kind: type[PersistentDocument] | type[ArchivedRecording] = (
            ArchivedRecording
            if stem == "recordings"
            else STORED_KINDS[COLLECTION_OF_FILE.get(stem, stem)]
        )
        for element in elements:
            kind.model_validate_json(element)
        validated[stem] = len(elements)

    filled = {stem for stem, count in validated.items() if count}
    assert {"business", "assistant_versions", "channels", "messages"} <= filled
    assert "recordings" in validated and "consent_records" in validated
