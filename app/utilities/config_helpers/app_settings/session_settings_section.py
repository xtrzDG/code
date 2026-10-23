"""
SESSION_IDLE_TIMEOUT_SECONDS, ADMIN_SESSION_IDLE_TIMEOUT_SECONDS and
ADMIN_SESSION_LIFETIME_SECONDS: when unused and admin sessions end;
WEBAUTHN_RP_ID and GEOIP_COUNTRY_DATABASE_PATH (sign_in_security_settings).
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
from app.utilities.config_helpers.app_settings.public_address_settings_section import (
    read_cabinet_base_url,
)
from app.utilities.config_helpers.app_settings.sign_in_security_settings import (
    read_geoip_country_database_path,
    read_webauthn_rp_id,
)


class SessionSettingsSection(TypedDict):
    """The `AppSettings` field of session expiry."""

    sessions: SessionSettings


def read_session_settings(
    environment_variables: Mapping[str, str],
    is_development: bool = False,
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
            webauthn_rp_id=read_webauthn_rp_id(
                environment_variables,
                read_cabinet_base_url(environment_variables, is_development),
            ),
            geoip_country_database_path=read_geoip_country_database_path(
                environment_variables
            ),
        )
    )
