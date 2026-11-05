"""
The use cases of the feature flags of staged rollouts (REL-08, 1260):
the admin's list, the SUPER admin's audited change after a step-up, and
the check of one business through the gate the release's code asks.
"""

from dependency_injector.providers import Factory

from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.platform_admins import PlatformAdminCheck
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.feature_flags import (
    FeatureFlagCheck,
    FeatureFlagCheckQuery,
    FeatureFlagCommand,
    FeatureFlagList,
    FeatureFlagListQuery,
    FeatureFlagView,
)
from app.use_cases.admin.feature_flags.check_feature_flag_use_case import (
    CheckFeatureFlagUseCase,
)
from app.use_cases.admin.feature_flags.list_feature_flags_use_case import (
    ListFeatureFlagsUseCase,
)
from app.use_cases.admin.feature_flags.set_feature_flag_use_case import (
    SetFeatureFlagUseCase,
)


def feature_flag_use_cases(
    repositories: RepositoriesContainer,
    utilities: UtilitiesContainer,
    time_provider: TimeProviderContainer,
    admin_check: Factory[PlatformAdminCheck],
) -> tuple[
    Factory[UseCaseContract[FeatureFlagListQuery, FeatureFlagList]],
    Factory[UseCaseContract[FeatureFlagCommand, FeatureFlagView]],
    Factory[UseCaseContract[FeatureFlagCheckQuery, FeatureFlagCheck]],
]:
    return (
        Factory(
            ListFeatureFlagsUseCase,
            authorize_platform_admin=admin_check,
            flag_repo=repositories.feature_flag_repo,
        ),
        Factory(
            SetFeatureFlagUseCase,
            authorize_platform_admin=admin_check,
            flag_repo=repositories.feature_flag_repo,
            audit_log_repo=repositories.audit_log_repo,
            step_up=utilities.step_up_guard,
            wall_clock=time_provider.microsecond_wall_clock,
        ),
        Factory(
            CheckFeatureFlagUseCase,
            authorize_platform_admin=admin_check,
            flag_gate=repositories.feature_flag_gate,
        ),
    )
