"""
What a previous key sealed or signed keeps working while it is in the ring:
Telegram webhooks, notification links and call recordings.
"""

from app.adapters.channels.telegram_channel_adapter import TelegramChannelAdapter
from app.adapters.recordings.encrypted_object_recording_storage_adapter import (
    EncryptedObjectRecordingStorageAdapter,
)
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.webhook_signatures import (
    derive_telegram_webhook_secret,
    is_matching_telegram_secret,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.notifications.staff_link_signer import StaffLinkSigner
from tests.security.previous_key_fakes import (
    DictObjectStorage,
    link_claims,
    recording,
    recording_location,
    webhook_payload,
)

OLD_KEY = PlatformSecret("old-key-of-the-platform-0123456789abcdef")
NEW_KEY = PlatformSecret("new-key-of-the-platform-fedcba9876543210")
BOT_TOKEN = ChannelSecret("123456789:AAH-telegram-bot-token")


def test_telegram_accepts_the_secret_of_any_key_in_the_ring() -> None:
    old_secret = derive_telegram_webhook_secret(OLD_KEY, BOT_TOKEN)
    new_secret = derive_telegram_webhook_secret(NEW_KEY, BOT_TOKEN)

    assert is_matching_telegram_secret(
        [NEW_KEY, OLD_KEY], BOT_TOKEN, webhook_payload(old_secret).signature_header
    )
    assert is_matching_telegram_secret(
        [NEW_KEY], BOT_TOKEN, webhook_payload(new_secret).signature_header
    )
    assert not is_matching_telegram_secret(
        [NEW_KEY], BOT_TOKEN, webhook_payload(old_secret).signature_header
    )
    assert not is_matching_telegram_secret(
        [], BOT_TOKEN, webhook_payload(new_secret).signature_header
    )


def test_the_telegram_adapter_verifies_with_the_ring() -> None:
    settings = assemble_app_settings({"ENCRYPTION_KEYS": f"{NEW_KEY},{OLD_KEY}"})
    adapter = TelegramChannelAdapter(
        telegram_client=None,  # type: ignore[arg-type]
        phone_number_parser=None,  # type: ignore[arg-type]
        app_settings=settings,
    )

    adapter.verify_signature(
        webhook_payload(derive_telegram_webhook_secret(OLD_KEY, BOT_TOKEN)), BOT_TOKEN
    )


def test_links_signed_with_a_previous_key_still_open() -> None:
    old_signer = StaffLinkSigner(OLD_KEY)
    rotated_signer = StaffLinkSigner(NEW_KEY, [OLD_KEY])
    token = old_signer.sign(link_claims())

    assert rotated_signer.read(token) == link_claims()
    assert StaffLinkSigner(NEW_KEY).read(token) is None
    assert old_signer.read(rotated_signer.sign(link_claims())) is None


def test_recordings_of_a_previous_key_still_play() -> None:
    storage = DictObjectStorage()
    location = recording_location()
    EncryptedObjectRecordingStorageAdapter(storage, OLD_KEY).store(
        location, recording()
    )
    rotated = EncryptedObjectRecordingStorageAdapter(
        storage, NEW_KEY, previous_master_secrets=[OLD_KEY]
    )

    part = rotated.read(location)

    assert part is not None and part.content == recording().content
    rotated.store(location, recording())
    assert (
        EncryptedObjectRecordingStorageAdapter(storage, NEW_KEY).read(location)
        is not None
    )
