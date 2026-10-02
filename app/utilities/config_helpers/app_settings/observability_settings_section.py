"""
LANGFUSE_*, SENTRY_*, LOG_FORMAT and the release: traces of model calls,
error reports and log lines.
"""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.constants.observability import LogFormat
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.booleans import IsLlmContentTraced
from app.schemas.typings.platform.constrained_floats import TraceSampleRate
from app.schemas.typings.platform.constrained_strings import ReleaseVersion
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    optional_setting,
    optional_text,
    parse_setting,
    read_boolean,
    read_float,
    read_text,
)

# Langfuse Cloud EU region (the concept keeps data in the EU).
DEFAULT_LANGFUSE_HOST: str = "https://cloud.langfuse.com"
# One request in twenty is traced: enough to see slow routes, cheap enough
# for the free Sentry plan.
DEFAULT_TRACES_SAMPLE_RATE: float = 0.05


class ObservabilitySettingsSection(TypedDict):
    """The `AppSettings` fields of tracing, error reporting and logs."""

    langfuse_public_key: PlatformIdentifier | None
    langfuse_secret_key: PlatformSecret | None
    sentry_dsn: PlatformSecret | None
    sentry_traces_sample_rate: TraceSampleRate
    release_version: ReleaseVersion | None
    log_format: LogFormat
    langfuse_host: PublicBaseUrl
    is_llm_content_traced: IsLlmContentTraced


def read_observability_settings(
    environment_variables: Mapping[str, str],
    is_production: bool,
) -> ObservabilitySettingsSection:
    return ObservabilitySettingsSection(
        langfuse_public_key=optional_text(
            environment_variables, "LANGFUSE_PUBLIC_KEY", PlatformIdentifier
        ),
        langfuse_secret_key=optional_text(
            environment_variables, "LANGFUSE_SECRET_KEY", PlatformSecret
        ),
        sentry_dsn=optional_text(environment_variables, "SENTRY_DSN", PlatformSecret),
        sentry_traces_sample_rate=parse_setting(
            "SENTRY_TRACES_SAMPLE_RATE",
            read_float(
                environment_variables,
                "SENTRY_TRACES_SAMPLE_RATE",
                DEFAULT_TRACES_SAMPLE_RATE,
            ),
            TraceSampleRate,
        ),
        release_version=read_release_version(environment_variables),
        log_format=read_log_format(environment_variables, is_production),
        langfuse_host=PublicBaseUrl(
            read_text(environment_variables, "LANGFUSE_HOST", DEFAULT_LANGFUSE_HOST)
        ),
        is_llm_content_traced=IsLlmContentTraced(
            read_boolean(environment_variables, "LANGFUSE_CAPTURE_CONTENT", False)
        ),
    )


def read_release_version(
    environment_variables: Mapping[str, str],
) -> ReleaseVersion | None:
    """
    APP_RELEASE names the deployed build; on Render it defaults to the commit
    Render built (RENDER_GIT_COMMIT, set by Render on every service).
    """

    explicit: ReleaseVersion | None = optional_setting(
        environment_variables, "APP_RELEASE", ReleaseVersion
    )
    if explicit is not None:
        return explicit

    return optional_setting(environment_variables, "RENDER_GIT_COMMIT", ReleaseVersion)


def read_log_format(
    environment_variables: Mapping[str, str],
    is_production: bool,
) -> LogFormat:
    """LOG_FORMAT: `json` (default in production) or `text` (elsewhere)."""

    default_format: LogFormat = LogFormat.JSON if is_production else LogFormat.TEXT
    return parse_setting(
        "LOG_FORMAT",
        read_text(environment_variables, "LOG_FORMAT", default_format).lower(),
        LogFormat,
    )
