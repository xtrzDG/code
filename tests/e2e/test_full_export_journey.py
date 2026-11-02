"""
End to end over HTTP: an owner leaving or switching asks for the full
export; the worker writes it and the one-time link downloads a ZIP with
the records, the assistant's versions and instructions, the call and
privacy settings, the channels without their credentials, the consent
ledger and the recordings' list, in the archive format its README names.
"""

import io
import json
import zipfile

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
    }
)


def test_the_full_export_takes_the_setup_along(workshop: Workshop) -> None:
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
        files = {name: archive.read(name) for name in archive.namelist()}
    assert CONFIGURATION_FILES <= set(files)
    assert b"Archive format 2." in files["README.txt"]
    versions = json.loads(files["assistant_versions.json"])
    assert versions and all(version["prompt_text"] for version in versions)
    [channel] = json.loads(files["channels.json"])
    assert channel["kind"] == "telegram"
    assert channel["encrypted_secret"] is None
    assert all(BUSINESS_BOT_TOKEN.encode() not in content for content in files.values())
    assert json.loads(files["recordings.json"]) == []
