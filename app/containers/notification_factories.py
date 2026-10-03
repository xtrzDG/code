"""Builders of the staff notification providers that depend on settings."""

from app.clients.webpush.web_push_client import WebPushClient
from app.schemas.configurations.app_settings import AppSettings
from app.utilities.notifications.staff_link_signer import StaffLinkSigner


def build_web_push_client(settings: AppSettings) -> WebPushClient | None:
    """
    Web Push when the VAPID key pair and subject are set, else None (device
    notifications are then off). A key pair that does not match stops the
    start (ValueError).
    """

    if (
        settings.web_push_vapid_public_key is None
        or settings.web_push_vapid_private_key is None
        or settings.web_push_vapid_subject is None
    ):
        return None

    return WebPushClient(
        private_key=settings.web_push_vapid_private_key,
        public_key=settings.web_push_vapid_public_key,
        subject=settings.web_push_vapid_subject,
    )


def build_staff_link_signer(settings: AppSettings) -> StaffLinkSigner:
    """
    Notification links signed with a key derived from the current key of
    the ring; links of the previous keys still open until they expire.
    """

    return StaffLinkSigner(settings.encryption_key, settings.previous_encryption_keys)
