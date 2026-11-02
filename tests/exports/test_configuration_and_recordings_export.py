"""
A full export takes the business's setup and its calls' audio along (Data
Act art. 26, GOV-07): the assistant's versions with their instructions, the
call and privacy settings, the channels without their credentials and the
consent ledger as JSON; every recording as its audio file under
recordings/ with a list (recordings.json) of what the archive holds and
where to download the rest. The README names the archive's format.
"""

import io
import json
import zipfile
from dataclasses import replace
from typing import Any

from base_pydantic_schemas import BaseDocument
from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.assistant_repositories import AssistantVersionRepository
from app.repositories.business_repositories import (
    BusinessProfileRepository,
    ChannelRepository,
)
from app.repositories.call_follow_up_repositories import CallSettingsRepository
from app.repositories.consent_record_repository import ConsentRecordRepository
from app.repositories.retention_settings_repositories import (
    BusinessPrivacySettingsRepository,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.consent_records import ConsentEvent, ConsentEventSource
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.business_privacy_settings import (
    BusinessPrivacySettingsDocument,
)
from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.domain.channels import ChannelDocument, WhatsAppNumberPin
from app.schemas.domain.consent_records import ConsentRecordDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.call_recordings import RecordingAudio, RecordingLocation
from app.schemas.typings.channels.strings import (
    ChannelExternalId,
    EncryptedChannelSecret,
)
from app.schemas.typings.conversations.constrained_strings import RecordingMediaType
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.use_cases.exports.business_archive import ARCHIVE_FORMAT
from app.use_cases.exports.configuration_archive import ConfigurationArchive
from app.use_cases.exports.recording_archive import CHUNK_BYTES, RecordingArchive
from app.utilities.calls.call_follow_up_keys import call_settings_id_of
from tests.channels.recording_storage_fakes import InMemoryRecordingStorage
from tests.compliance.two_tenants import TwoTenants, seed_two_tenants
from tests.privacy.business_export_bed import BusinessExportBed
from tests.storage.document_evolution.sample_documents import sample_document

SEALED_TOKEN: str = "sealed-token-never-exported"
SEALED_PIN: str = "sealed-pin-never-exported"
# Two chunks and a bit: the copy is read a megabyte at a time.
LONG_AUDIO: bytes = bytes(range(256)) * (2 * CHUNK_BYTES // 256 + 3)


def business_copy[Document: BaseDocument](
    document_type: type[Document], collection: str, tenants: TwoTenants
) -> Document:
    """A sample document of the collection, made the business's own."""

    sample = sample_document(document_type, DocumentCollectionName(collection))
    return sample.model_copy(update={"business_id": tenants.business.id})


def seed_configuration(tenants: TwoTenants) -> ConfigurationArchive:
    business = tenants.business
    profiles = BusinessProfileRepository(
        InMemoryDocumentCollectionAdapter(BusinessProfileDocument)
    )
    profiles.save(business_copy(BusinessProfileDocument, "business_profiles", tenants))
    versions = AssistantVersionRepository(
        InMemoryDocumentCollectionAdapter(AssistantVersionDocument)
    )
    versions.save(
        business_copy(AssistantVersionDocument, "assistant_versions", tenants)
    )
    call_settings = CallSettingsRepository(
        InMemoryDocumentCollectionAdapter(CallSettingsDocument)
    )
    call_settings.save(
        business_copy(CallSettingsDocument, "call_settings", tenants).model_copy(
            update={"id": call_settings_id_of(business.id)}
        )
    )
    channels = ChannelRepository(InMemoryDocumentCollectionAdapter(ChannelDocument))
    channels.save(
        ChannelDocument(
            business_id=business.id,
            kind=ChannelKind.WHATSAPP,
            external_id=ChannelExternalId("1055"),
            encrypted_secret=EncryptedChannelSecret(SEALED_TOKEN),
            whatsapp_registration_pins=[
                WhatsAppNumberPin(
                    phone_number_id=ChannelExternalId("1055"),
                    encrypted_pin=EncryptedChannelSecret(SEALED_PIN),
                )
            ],
        )
    )
    ledger = ConsentRecordRepository(
        InMemoryDocumentCollectionAdapter(ConsentRecordDocument)
    )
    ledger.append(
        ConsentRecordDocument(
            business_id=business.id,
            contact_id=tenants.visitor.contact.id,
            event=ConsentEvent.GIVEN,
            source=ConsentEventSource.BOOKING_PAGE,
        )
    )
    return ConfigurationArchive(
        profile_repo=profiles,
        assistant_version_repo=versions,
        call_settings_repo=call_settings,
        privacy_settings_repo=BusinessPrivacySettingsRepository(
            InMemoryDocumentCollectionAdapter(BusinessPrivacySettingsDocument)
        ),
        channel_repo=channels,
        consent_record_repo=ledger,
    )


def written_archive(
    tenants: TwoTenants,
    configuration: ConfigurationArchive | None = None,
    recordings: RecordingArchive | None = None,
) -> dict[str, bytes]:
    builder = replace(
        BusinessExportBed(tenants).archive_builder,
        configuration=configuration,
        recordings=recordings,
    )
    target = io.BytesIO()
    builder.write(
        tenants.business,
        tenants.business.default_language,
        Microseconds(1_790_000_000_000_000),
        tenants.owner_id,
        target,
    )
    with zipfile.ZipFile(io.BytesIO(target.getvalue())) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def as_json(files: dict[str, bytes], name: str) -> Any:
    return json.loads(files[name])


def test_the_setup_travels_with_the_export_without_credentials() -> None:
    tenants = seed_two_tenants()

    files = written_archive(tenants, seed_configuration(tenants))

    [version] = as_json(files, "assistant_versions.json")
    assert version["prompt_text"]
    assert len(as_json(files, "business_profile.json")) == 1
    assert len(as_json(files, "call_settings.json")) == 1
    [privacy] = as_json(files, "privacy_settings.json")
    assert privacy["conversation_retention_days"] > 0
    [channel] = as_json(files, "channels.json")
    assert channel["kind"] == "whatsapp"
    assert channel["encrypted_secret"] is None
    assert channel["whatsapp_registration_pins"] == []
    assert all(
        SEALED_TOKEN.encode() not in content and SEALED_PIN.encode() not in content
        for content in files.values()
    )
    [consent] = as_json(files, "consent_records.json")
    assert consent["contact_id"] == str(tenants.visitor.contact.id)
    assert f"Archive format {ARCHIVE_FORMAT}." in files["README.txt"].decode()


def test_every_recording_is_copied_and_listed() -> None:
    tenants = seed_two_tenants()
    storage = InMemoryRecordingStorage()
    first, second = (
        tenants.visitor.conversation_call,
        tenants.visitor.phone_matched_call,
    )
    assert first.recording_path is not None and second.recording_path is not None
    storage.store(
        RecordingLocation(business_id=first.business_id, path=first.recording_path),
        RecordingAudio(content=LONG_AUDIO, media_type=RecordingMediaType("audio/mpeg")),
    )

    files = written_archive(
        tenants,
        recordings=RecordingArchive(tenants.testbed.call_repo, storage),
    )

    listed = {entry["call_id"]: entry for entry in as_json(files, "recordings.json")}
    copied = listed[str(first.id)]
    assert (copied["status"], copied["file"]) == (
        "included",
        f"recordings/{first.id}.mp3",
    )
    assert copied["total_bytes"] == len(LONG_AUDIO)
    assert files[f"recordings/{first.id}.mp3"] == LONG_AUDIO
    assert copied["download_path"] == (
        f"/v1/businesses/{tenants.business.id}/calls/{first.id}/recording"
    )
    # The storage no longer has the second one: listed, never a failure.
    missing = listed[str(second.id)]
    assert (missing["status"], missing["file"]) == ("unavailable", None)


def test_recordings_past_the_size_limit_are_listed_to_download() -> None:
    tenants = seed_two_tenants()
    storage = InMemoryRecordingStorage()
    first = tenants.visitor.conversation_call
    assert first.recording_path is not None
    storage.store(
        RecordingLocation(business_id=first.business_id, path=first.recording_path),
        RecordingAudio(content=LONG_AUDIO, media_type=RecordingMediaType("audio/wav")),
    )

    files = written_archive(
        tenants,
        recordings=RecordingArchive(
            tenants.testbed.call_repo, storage, max_bytes=len(LONG_AUDIO) - 1
        ),
    )

    [left_out] = [
        entry
        for entry in as_json(files, "recordings.json")
        if entry["call_id"] == str(first.id)
    ]
    assert (left_out["status"], left_out["file"]) == ("left_out", None)
    assert left_out["media_type"] == "audio/wav"
    assert not any(name.startswith("recordings/") for name in files)
