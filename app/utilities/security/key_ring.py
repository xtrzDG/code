"""The platform's key ring: the current key first, then the previous ones."""

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.typings.platform.strings import PlatformSecret


def key_ring(settings: AppSettings) -> list[PlatformSecret]:
    """
    Every key that may have sealed or signed something still in use, the
    current one (which seals and signs everything new) first. Empty without
    any key (development).
    """

    if settings.encryption_key is None:
        return []

    return [settings.encryption_key, *settings.previous_encryption_keys]
