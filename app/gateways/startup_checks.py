"""
Checks both entry points (the API and the worker) run before serving:
production starts only on production settings (no unset, test or
development value), every flow of personal data the settings configure
reaches only a provider the sub-processor list (DPA section 8) names for it
on that day, and the database roles the pools log in as keep businesses
apart (migration 1200).
"""

import logging

from app.containers.app import AppContainer
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.dto.database_roles import PoolRole
from app.schemas.dto.processor_uses import UncoveredProcessorUse
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.platform.strings import ProductionSettingProblem
from app.schemas.typings.storage.strings import DatabaseRoleProblem
from app.utilities.config_helpers.llm_provider_keys import report_unusable_fallback
from app.utilities.config_helpers.production.production_problems import (
    find_production_problems,
    require_production_settings,
)
from app.utilities.legal.processor_coverage import configure_uses, find_uncovered_uses
from app.utilities.legal.subprocessor_dates import utc_day
from app.utilities.storage.database_role_rules import find_role_problems

LOGGER: logging.Logger = logging.getLogger(__name__)


def run_startup_checks(app_container: AppContainer) -> None:
    """
    Production's requirements first, then the sub-processor list and the
    database roles (each refuses to start in production); a fallback model
    whose provider has no key is reported once and skipped.
    """

    check_production_requirements(app_container)
    check_processor_uses(app_container)
    check_database_roles(app_container)
    report_unusable_fallback(app_container.config.app_settings())


def check_production_requirements(
    app_container: AppContainer,
) -> list[ProductionSettingProblem]:
    """
    APP_ENV=production refuses to start on any unset, test or development
    setting (`find_production_problems`, every problem in one error) and
    without a channel that carries login codes (nobody could sign in). The
    key ring and the seller's VAT rate are resolved here as well, so their
    own refusals (a missing, public or short ENCRYPTION_KEY; a VAT-registered
    seller of a country without a known rate) stop the start, not the first
    secret or invoice. Elsewhere nothing is checked. Returns the problems.
    """

    settings: AppSettings = app_container.config.app_settings()
    if settings.environment is not DeploymentEnvironment.PRODUCTION:
        return []

    problems: list[ProductionSettingProblem] = find_production_problems(settings)
    if not app_container.facilitators.otp_delivery_facilitator().available_channels():
        problems.append(
            ProductionSettingProblem(
                "No login code provider is configured, so nobody could sign in: "
                "set TWILIO_* (SMS), TELEGRAM_GATEWAY_API_TOKEN, WHATSAPP_OTP_* "
                'or SMTP_* (.env.example, "Login codes").'
            )
        )
    require_production_settings(settings, problems)
    app_container.adapters.secret_cipher()
    app_container.registries.tax_policy_registry()
    return problems


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


def check_database_roles(app_container: AppContainer) -> list[DatabaseRoleProblem]:
    """
    A pool whose login role breaks tenant isolation (DATABASE_URL_TENANT
    naming the migration role, a superuser or a member of
    workshop_platform; a platform role outside its group) stops the process
    in production and is logged as a warning elsewhere. So does a pool
    whose role cannot be asked at all (an unreachable or wrong
    DATABASE_URL_PLATFORM, a revoked login, a role name the guide rules
    out): production never serves with a pool it could not check, and
    elsewhere the readiness probe, which asks both pools, reports it.
    Returns the problems found.
    """

    settings: AppSettings = app_container.config.app_settings()
    is_production: bool = settings.environment is DeploymentEnvironment.PRODUCTION
    try:
        pool_roles: list[PoolRole] = (
            app_container.adapters.database_roles().inspect_pool_roles()
        )
    except ExternalServiceError as error:
        if is_production:
            raise ValidationFailedError(
                f"The database roles could not be checked: {error}"
            ) from error

        LOGGER.warning("The database roles could not be checked: %s", error)
        return []

    problems: list[DatabaseRoleProblem] = find_role_problems(pool_roles)
    if not problems:
        return problems

    message: str = (
        "The database roles do not keep businesses apart: "
        + "; ".join(str(problem) for problem in problems)
        + '. See docs/operations/deploys.md, "Database roles".'
    )
    if is_production:
        raise ValidationFailedError(message)

    LOGGER.warning(message)
    return problems
