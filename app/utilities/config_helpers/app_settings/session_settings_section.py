"""
SESSION_IDLE_TIMEOUT_SECONDS, ADMIN_SESSION_IDLE_TIMEOUT_SECONDS and
ADMIN_SESSION_LIFETIME_SECONDS: when unused and admin sessions end.
"""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.configurations.session_settings import (
    DEFAULT_ADMIN_SESSION_IDLE_TIMEOUT_SECONDS,
    DEFAULT_ADMIN_SESSION_LIFETIME_SECONDS,
    DEFAULT_SESSION_IDLE_TIMEOUT_SECONDS,
    SessionSettings,
)
from app.schemas.typings.users.constrained_integers import (
    SessionIdleTimeoutSeconds,
    SessionLifetimeSeconds,
)
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    parse_setting,
    read_integer,
)


class SessionSettingsSection(TypedDict):
    """The `AppSettings` field of session expiry."""

    sessions: SessionSettings


def read_session_settings(
    environment_variables: Mapping[str, str],
) -> SessionSettingsSection:
    return SessionSettingsSection(
        sessions=SessionSettings(
            idle_timeout_seconds=parse_setting(
                "SESSION_IDLE_TIMEOUT_SECONDS",
                read_integer(
                    environment_variables,
                    "SESSION_IDLE_TIMEOUT_SECONDS",
                    DEFAULT_SESSION_IDLE_TIMEOUT_SECONDS,
                ),
                SessionIdleTimeoutSeconds,
            ),
            admin_idle_timeout_seconds=parse_setting(
                "ADMIN_SESSION_IDLE_TIMEOUT_SECONDS",
                read_integer(
                    environment_variables,
                    "ADMIN_SESSION_IDLE_TIMEOUT_SECONDS",
                    DEFAULT_ADMIN_SESSION_IDLE_TIMEOUT_SECONDS,
                ),
                SessionIdleTimeoutSeconds,
            ),
            admin_lifetime_seconds=parse_setting(
                "ADMIN_SESSION_LIFETIME_SECONDS",
                read_integer(
                    environment_variables,
                    "ADMIN_SESSION_LIFETIME_SECONDS",
                    DEFAULT_ADMIN_SESSION_LIFETIME_SECONDS,
                ),
                SessionLifetimeSeconds,
            ),
        )
    )
