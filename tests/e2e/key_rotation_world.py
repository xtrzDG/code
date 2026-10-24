"""
A platform whose secrets were sealed before a key rotation: the workshop
runs with the ring (new key, old key) and some stored secrets are sealed
with the old key alone, as they were before ENCRYPTION_KEYS got the new one.
"""

from app.adapters.security.secret_cipher_adapter import SecretCipherAdapter
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.calendar import CalendarConnectionDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.typings.bookings.strings import ExternalCalendarId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.channels.strings import ChannelExternalId, ChannelSecret
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.e2e.harness import Workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT

OLD_KEY: str = E2E_ENVIRONMENT["ENCRYPTION_KEY"]
NEW_KEY: str = "e2e-rotated-encryption-secret-fedcba987654"  # gitleaks:allow
FOREIGN_KEY: str = "a-key-this-platform-never-had-0123456789"  # gitleaks:allow
ROTATING_ENVIRONMENT: dict[str, str] = {**E2E_ENVIRONMENT, "ENCRYPTION_KEYS": NEW_KEY}
REFRESH_TOKEN: ChannelSecret = ChannelSecret("1//google-refresh-token")
ACCESS_TOKEN: ChannelSecret = ChannelSecret("ya29.google-access-token")
PAGE_TOKEN: ChannelSecret = ChannelSecret("EAAG-whatsapp-system-token")


def cipher_of(key: str) -> SecretCipherAdapter:
    return SecretCipherAdapter(assemble_app_settings({"ENCRYPTION_KEYS": key}))


def seal_with_old_key(workshop: Workshop, channel_id: str) -> None:
    """The Telegram channel's token as the old key alone sealed it."""

    container = workshop.container
    channel_repo = container.repositories.channel_repo()
    with container.utilities.storage_scope().platform_wide():
        channel = channel_repo.get(ChannelId(channel_id))
        assert channel is not None and channel.encrypted_secret is not None
        token = cipher_of(NEW_KEY).decrypt(channel.encrypted_secret)
        channel_repo.save(
            channel.model_copy(
                update={"encrypted_secret": cipher_of(OLD_KEY).encrypt(token)}
            )
        )


def store_old_secrets(workshop: Workshop, business_id: str, owner_id: str) -> None:
    """A calendar sealed with the old key and a channel no key can open."""

    container = workshop.container
    now = workshop.container.time_provider.microsecond_wall_clock().now_unix()
    old = cipher_of(OLD_KEY)
    with container.utilities.storage_scope().platform_wide():
        container.repositories.calendar_connection_repo().save(
            CalendarConnectionDocument(
                business_id=BusinessId(business_id),
                calendar_id=ExternalCalendarId("primary"),
                encrypted_refresh_token=old.encrypt(REFRESH_TOKEN),
                encrypted_access_token=old.encrypt(ACCESS_TOKEN),
                connected_by=UserId(owner_id),
                created_at=now,
                updated_at=now,
            )
        )
        container.repositories.channel_repo().save(
            ChannelDocument(
                business_id=BusinessId(business_id),
                kind=ChannelKind.WHATSAPP,
                external_id=ChannelExternalId("15550001111"),
                encrypted_secret=cipher_of(FOREIGN_KEY).encrypt(PAGE_TOKEN),
                status=ChannelStatus.CONNECTED,
                created_at=now,
                updated_at=now,
            )
        )


def stored_secrets_open_with_the_new_key_alone(
    workshop: Workshop, business_id: str
) -> list[ChannelSecret]:
    container = workshop.container
    new = cipher_of(NEW_KEY)
    with container.utilities.storage_scope().platform_wide():
        channels = container.repositories.channel_repo().list_by_business(
            BusinessId(business_id)
        )
        calendar = container.repositories.calendar_connection_repo().get_by_business(
            BusinessId(business_id)
        )
    assert calendar is not None and calendar.encrypted_access_token is not None
    secrets: list[ChannelSecret] = [
        new.decrypt(calendar.encrypted_refresh_token),
        new.decrypt(calendar.encrypted_access_token),
    ]
    secrets.extend(
        new.decrypt(channel.encrypted_secret)
        for channel in channels
        if channel.encrypted_secret is not None and channel.kind is ChannelKind.TELEGRAM
    )
    return secrets
