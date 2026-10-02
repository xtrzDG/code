"""LANGFUSE_* and SENTRY_DSN: traces of model calls and error reports."""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.booleans import IsLlmContentTraced
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    optional_text,
    read_boolean,
    read_text,
)

# Langfuse Cloud EU region (the concept keeps data in the EU).
DEFAULT_LANGFUSE_HOST: str = "https://cloud.langfuse.com"


class ObservabilitySettingsSection(TypedDict):
    """The `AppSettings` fields of tracing and error reporting."""

    langfuse_public_key: PlatformIdentifier | None
    langfuse_secret_key: PlatformSecret | None
    sentry_dsn: PlatformSecret | None
    langfuse_host: PublicBaseUrl
    is_llm_content_traced: IsLlmContentTraced


def read_observability_settings(
    environment_variables: Mapping[str, str],
) -> ObservabilitySettingsSection:
    return ObservabilitySettingsSection(
        langfuse_public_key=optional_text(
            environment_variables, "LANGFUSE_PUBLIC_KEY", PlatformIdentifier
        ),
        langfuse_secret_key=optional_text(
            environment_variables, "LANGFUSE_SECRET_KEY", PlatformSecret
        ),
        sentry_dsn=optional_text(environment_variables, "SENTRY_DSN", PlatformSecret),
        langfuse_host=PublicBaseUrl(
            read_text(environment_variables, "LANGFUSE_HOST", DEFAULT_LANGFUSE_HOST)
        ),
        is_llm_content_traced=IsLlmContentTraced(
            read_boolean(environment_variables, "LANGFUSE_CAPTURE_CONTENT", False)
        ),
    )
