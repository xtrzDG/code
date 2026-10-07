"""PUBLIC_API_REQUESTS_PER_MINUTE and WEBHOOK_DISABLE_AFTER_FAILURES."""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.configurations.public_api_settings import (
    DEFAULT_FAILURES_BEFORE_DISABLE,
    DEFAULT_REQUESTS_PER_MINUTE,
    PublicApiSettings,
)
from app.schemas.typings.integrations.constrained_integers import (
    PublicApiRequestsPerMinute,
    WebhookFailuresBeforeDisable,
)
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    read_integer,
)


class PublicApiSettingsSection(TypedDict):
    """The `AppSettings` field of the public API and the webhooks."""

    public_api: PublicApiSettings


def read_public_api_settings(
    environment_variables: Mapping[str, str],
) -> PublicApiSettingsSection:
    """Both variables are optional (see `PublicApiSettings`)."""

    return PublicApiSettingsSection(
        public_api=PublicApiSettings(
            requests_per_minute=PublicApiRequestsPerMinute(
                read_integer(
                    environment_variables,
                    "PUBLIC_API_REQUESTS_PER_MINUTE",
                    int(DEFAULT_REQUESTS_PER_MINUTE),
                )
            ),
            webhook_failures_before_disable=WebhookFailuresBeforeDisable(
                read_integer(
                    environment_variables,
                    "WEBHOOK_DISABLE_AFTER_FAILURES",
                    int(DEFAULT_FAILURES_BEFORE_DISABLE),
                )
            ),
        )
    )
