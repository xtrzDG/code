"""
Checks both entry points (the API and the worker) run before serving: every
flow of personal data the settings configure reaches only a provider the
sub-processor list (DPA section 8) names for it on that day.
"""

import logging

from app.containers.app import AppContainer
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.dto.processor_uses import UncoveredProcessorUse
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.utilities.legal.processor_coverage import configure_uses, find_uncovered_uses
from app.utilities.legal.subprocessor_dates import utc_day

LOGGER: logging.Logger = logging.getLogger(__name__)


def check_processor_uses(app_container: AppContainer) -> list[UncoveredProcessorUse]:
    """
    A configured flow whose provider no sub-processor entry in force covers
    (e.g. OpenAI deployment, ANTHROPIC_API_KEY set and
    QUALITY_SAMPLING_JUDGE_SAME_PROVIDER=false before the owners' notice of
    Anthropic as quality judge has run its 30 days) stops the process in
    production and is logged as a warning elsewhere. Returns what is
    uncovered.
    """

    settings: AppSettings = app_container.config.app_settings()
    registries = app_container.registries
    uncovered: list[UncoveredProcessorUse] = find_uncovered_uses(
        configure_uses(registries.processor_use_registry().list_uses(), settings),
        registries.subprocessor_registry().list_entries(),
        utc_day(app_container.time_provider.microsecond_wall_clock().now_unix()),
    )
    if not uncovered:
        return uncovered

    message: str = (
        "Personal data would reach a provider the sub-processor list (DPA "
        "section 8) does not name for that purpose: "
        + "; ".join(
            f"{item.flow.value} -> {item.client_module} ("
            f"{', '.join(category.value for category in item.data_categories)}; "
            f"set by {', '.join(str(name) for name in item.provider_settings)})"
            for item in uncovered
        )
        + ". Change these settings, or add the use to "
        "app/registries/legal and let its 30-day notice to owners run first."
    )
    if settings.environment is DeploymentEnvironment.PRODUCTION:
        raise ValidationFailedError(message)

    LOGGER.warning(message)
    return uncovered
