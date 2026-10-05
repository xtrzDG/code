"""Assemble AppSettings from environment variables (the external boundary).

Each `*_settings_section` module reads the variables of one topic; the
assembler checks what spans topics first and composes the sections in the
order of the `AppSettings` fields.
"""

import os
from collections.abc import Mapping

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.config_helpers.app_settings.backup_settings_section import (
    read_backup_settings,
)
from app.utilities.config_helpers.app_settings.capacity_settings_section import (
    read_capacity_settings,
)
from app.utilities.config_helpers.app_settings.compliance_settings_section import (
    read_compliance_settings,
)
from app.utilities.config_helpers.app_settings.encryption_key_settings_section import (
    read_encryption_key_settings,
)
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    optional_text,
    read_text,
)
from app.utilities.config_helpers.app_settings.growth_settings_section import (
    read_growth_settings,
)
from app.utilities.config_helpers.app_settings.integration_settings_section import (
    read_integration_settings,
)
from app.utilities.config_helpers.app_settings.llm_settings_section import (
    read_llm_provider,
    read_llm_settings,
)
from app.utilities.config_helpers.app_settings.login_settings_section import (
    read_login_settings,
    read_otp_code_logging,
)
from app.utilities.config_helpers.app_settings.media_settings_section import (
    read_media_settings,
)
from app.utilities.config_helpers.app_settings.mfa_settings_section import (
    read_mfa_settings,
)
from app.utilities.config_helpers.app_settings.observability_settings_section import (
    read_observability_settings,
)
from app.utilities.config_helpers.app_settings.otp_provider_settings_section import (
    check_login_code_providers,
    read_otp_provider_settings,
    read_smtp_security,
)
from app.utilities.config_helpers.app_settings.platform_admin_settings_section import (
    read_platform_admin_settings,
)
from app.utilities.config_helpers.app_settings.platform_alert_settings_section import (
    read_platform_alert_settings,
)
from app.utilities.config_helpers.app_settings.privacy_settings_section import (
    read_privacy_settings,
)
from app.utilities.config_helpers.app_settings.public_address_settings_section import (
    read_public_address_settings,
)
from app.utilities.config_helpers.app_settings.public_site_settings_section import (
    read_public_site_settings,
)
from app.utilities.config_helpers.app_settings.quality_settings_section import (
    read_quality_settings,
)
from app.utilities.config_helpers.app_settings.recordings_settings_section import (
    read_recording_storage_settings,
)
from app.utilities.config_helpers.app_settings.reply_safety_settings_section import (
    read_reply_safety_settings,
)
from app.utilities.config_helpers.app_settings.reply_speed_settings_section import (
    read_reply_speed_settings,
)
from app.utilities.config_helpers.app_settings.runtime_settings_section import (
    read_runtime_settings,
)
from app.utilities.config_helpers.app_settings.seller_settings_section import (
    read_seller_settings,
)
from app.utilities.config_helpers.app_settings.session_settings_section import (
    read_session_settings,
)
from app.utilities.config_helpers.app_settings.spend_guard_settings_section import (
    read_spend_guard_settings,
)
from app.utilities.config_helpers.app_settings.support_settings_section import (
    read_support_settings,
)
from app.utilities.config_helpers.app_settings.voice_settings_section import (
    read_voice_settings,
)
from app.utilities.config_helpers.app_settings.web_push_settings_section import (
    read_web_push_settings,
)


def get_app_settings() -> AppSettings:
    """Assemble validated settings from the process environment."""

    return assemble_app_settings(os.environ)


def assemble_app_settings(environment_variables: Mapping[str, str]) -> AppSettings:
    """Assemble validated settings from an explicit variable mapping."""

    environment = DeploymentEnvironment(
        read_text(environment_variables, "APP_ENV", DeploymentEnvironment.DEVELOPMENT)
    )
    is_development: bool = environment is not DeploymentEnvironment.PRODUCTION
    llm_provider = read_llm_provider(environment_variables)
    is_otp_code_logging_enabled: bool = read_otp_code_logging(
        environment_variables, is_development
    )
    check_login_code_providers(environment_variables)
    smtp_security = read_smtp_security(environment_variables)
    database_url: DatabaseUrl | None = optional_text(
        environment_variables, "DATABASE_URL", DatabaseUrl
    )
    key_ring = read_encryption_key_settings(environment_variables)

    return AppSettings(
        environment=environment,
        **read_public_address_settings(environment_variables, is_development),
        database_url=database_url,
        live_events_database_url=optional_text(
            environment_variables, "LIVE_EVENTS_DATABASE_URL", DatabaseUrl
        ),
        **key_ring,
        **read_llm_settings(environment_variables, llm_provider),
        **read_login_settings(environment_variables, is_otp_code_logging_enabled),
        **read_mfa_settings(environment_variables),
        **read_compliance_settings(environment_variables),
        **read_platform_admin_settings(environment_variables),
        **read_otp_provider_settings(environment_variables, smtp_security),
        **read_voice_settings(environment_variables, is_production=not is_development),
        **read_integration_settings(environment_variables),
        **read_web_push_settings(environment_variables),
        **read_observability_settings(
            environment_variables, is_production=not is_development
        ),
        **read_runtime_settings(
            environment_variables,
            environment=environment,
            has_database=database_url is not None,
        ),
        **read_capacity_settings(environment_variables),
        **read_recording_storage_settings(
            environment_variables,
            has_encryption_key=key_ring["encryption_key"] is not None,
        ),
        **read_backup_settings(environment_variables),
        **read_media_settings(environment_variables),
        **read_reply_speed_settings(environment_variables, llm_provider),
        **read_reply_safety_settings(environment_variables, llm_provider),
        **read_platform_alert_settings(environment_variables),
        **read_session_settings(environment_variables),
        **read_support_settings(environment_variables),
        **read_privacy_settings(environment_variables),
        **read_seller_settings(environment_variables),
        **read_quality_settings(environment_variables),
        **read_public_site_settings(environment_variables),
        **read_spend_guard_settings(environment_variables),
        **read_growth_settings(environment_variables),
    )
