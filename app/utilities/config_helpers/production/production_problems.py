"""
What production refuses to start with: every unset, test or development
setting, each named by its variable (docs/operations/go-live.md,
"Production refuses to start"). Development, tests and the preview stand
never ask (`APP_ENV` is not `production` there).
"""

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.platform.strings import ProductionSettingProblem
from app.utilities.config_helpers.production.address_requirements import (
    find_address_problems,
)
from app.utilities.config_helpers.production.database_tls_requirements import (
    find_database_tls_problems,
)
from app.utilities.config_helpers.production.model_requirements import (
    find_model_problems,
)
from app.utilities.config_helpers.production.platform_requirements import (
    find_platform_problems,
)
from app.utilities.config_helpers.production.secret_requirements import (
    find_provider_secret_problems,
)
from app.utilities.config_helpers.production.sign_in_requirements import (
    find_sign_in_problems,
)


def find_production_problems(settings: AppSettings) -> list[ProductionSettingProblem]:
    """Why these settings cannot serve production; empty when they can."""

    return [
        *find_platform_problems(settings),
        *find_database_tls_problems(settings),
        *find_address_problems(settings),
        *find_sign_in_problems(settings),
        *find_model_problems(settings),
        *find_provider_secret_problems(settings),
    ]


def require_production_settings(
    settings: AppSettings,
    problems: list[ProductionSettingProblem],
) -> None:
    """
    In production: raise with every problem, one per line, so one deploy
    log shows everything to fix. Elsewhere: nothing.

    Raises:
        ValidationFailedError: production with at least one problem.
    """

    if settings.environment is not DeploymentEnvironment.PRODUCTION or not problems:
        return

    raise ValidationFailedError(
        "Production refuses to start (APP_ENV=production):\n"
        + "\n".join(f"- {problem}" for problem in problems)
        + '\nSee docs/operations/go-live.md, "Production refuses to start".'
    )
