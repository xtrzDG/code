"""WEB_PUSH_VAPID_*: the platform key of notifications on cabinet devices."""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.notifications.constrained_strings import (
    VapidPublicKey,
    VapidSubject,
)
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    optional_text,
)

WEB_PUSH_VARIABLES: tuple[str, ...] = (
    "WEB_PUSH_VAPID_PUBLIC_KEY",
    "WEB_PUSH_VAPID_PRIVATE_KEY",
    "WEB_PUSH_VAPID_SUBJECT",
)


class WebPushSettingsSection(TypedDict):
    """The `AppSettings` fields of Web Push (all set, or none: push is off)."""

    web_push_vapid_public_key: VapidPublicKey | None
    web_push_vapid_private_key: PlatformSecret | None
    web_push_vapid_subject: VapidSubject | None


def read_web_push_settings(
    environment_variables: Mapping[str, str],
) -> WebPushSettingsSection:
    """
    The VAPID key pair (`npx web-push generate-vapid-keys`) and the contact
    push services may write to. Set completely or not at all, so a typo
    stops the start instead of silently turning device notifications off.
    """

    present: list[str] = [
        name
        for name in WEB_PUSH_VARIABLES
        if environment_variables.get(name, "").strip() != ""
    ]
    if present and len(present) != len(WEB_PUSH_VARIABLES):
        raise ValidationFailedError(
            "Device notifications need WEB_PUSH_VAPID_PUBLIC_KEY, "
            "WEB_PUSH_VAPID_PRIVATE_KEY and WEB_PUSH_VAPID_SUBJECT together."
        )

    return WebPushSettingsSection(
        web_push_vapid_public_key=optional_text(
            environment_variables, "WEB_PUSH_VAPID_PUBLIC_KEY", VapidPublicKey
        ),
        web_push_vapid_private_key=optional_text(
            environment_variables, "WEB_PUSH_VAPID_PRIVATE_KEY", PlatformSecret
        ),
        web_push_vapid_subject=optional_text(
            environment_variables, "WEB_PUSH_VAPID_SUBJECT", VapidSubject
        ),
    )
