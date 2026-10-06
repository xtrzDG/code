"""The checks behind the platform alert rules, built from the container edges."""

from dependency_injector.providers import Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.use_cases.data_task_use_cases import DataTaskUseCasesContainer
from app.use_cases.admin.alerts.alert_checks import PlatformAlertChecks
from app.use_cases.admin.alerts.burn_rate_alert_checks import burn_rate_alert_checks
from app.use_cases.admin.alerts.spend_alert_checks import SpendAlertChecks


def platform_alert_checks_factory(
    repositories: RepositoriesContainer,
    adapters: AdaptersContainer,
    config: ConfigContainer,
    data_task_use_cases: DataTaskUseCasesContainer,
) -> Factory[PlatformAlertChecks]:
    """
    The indexed counts, signal counters, worker pulses and spend sums of the
    `platform_alerts` job, the post-deploy data tasks (1164), and the SLOs'
    burn rates over the service level slots (1163).
    """

    return Factory(
        PlatformAlertChecks,
        system_health_repo=repositories.system_health_repo,
        platform_activity_repo=repositories.platform_activity_repo,
        signal_counter=adapters.signal_counter,
        quality_totals_repo=repositories.quality_totals_repo,
        spend_checks=Factory(
            SpendAlertChecks,
            usage_spend_repo=repositories.usage_spend_repo,
            daily_budget_micro_usd=(
                config.app_settings.provided.spend_guard.provided.platform_daily_budget_micro_usd
            ),
        ),
        data_task_checks=data_task_use_cases.data_task_alert_checks,
        extra_checks=Factory(
            burn_rate_alert_checks, slot_repo=repositories.service_level_slot_repo
        ),
    )
