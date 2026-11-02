"""The checks behind the platform alert rules, built from the container edges."""

from dependency_injector.providers import Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.use_cases.data_task_use_cases import DataTaskUseCasesContainer
from app.use_cases.admin.alerts.alert_checks import PlatformAlertChecks
from app.use_cases.admin.alerts.extra_alert_checks import extra_alert_checks
from app.use_cases.admin.alerts.platform_health_alert_checks import (
    PlatformHealthAlertChecks,
)
from app.use_cases.admin.alerts.safety_alert_checks import PlatformSafetyAlertChecks
from app.use_cases.admin.alerts.spend_alert_checks import SpendAlertChecks
from app.use_cases.admin.alerts.voice_alert_checks import VoiceHealthAlertCheck


def platform_alert_checks_factory(
    repositories: RepositoriesContainer,
    adapters: AdaptersContainer,
    config: ConfigContainer,
    data_task_use_cases: DataTaskUseCasesContainer,
) -> Factory[PlatformAlertChecks]:
    """
    The indexed counts, signal counters, worker pulses and spend sums of the
    `platform_alerts` job, the post-deploy data tasks (1164), the SLOs'
    burn rates over the service level slots (1163) and the freshest worker
    pulse (WORKER_DOWN, 1173), the audit log's hour of entries and the
    checks of its chains (1193), and the voice platform's API failures and
    finished-call reports (VOICE_HEALTH), the daily budget stop, the
    periodic jobs' heartbeats and the daily payment reconciliation (1230).
    """

    spend_guard = config.app_settings.provided.spend_guard.provided
    spend_checks = Factory(
        SpendAlertChecks,
        usage_spend_repo=repositories.usage_spend_repo,
        daily_budget_micro_usd=spend_guard.platform_daily_budget_micro_usd,
        stop_percent=spend_guard.platform_spend_stop_percent,
    )
    return Factory(
        PlatformAlertChecks,
        system_health_repo=repositories.system_health_repo,
        platform_activity_repo=repositories.platform_activity_repo,
        signal_counter=adapters.signal_counter,
        quality_totals_repo=repositories.quality_totals_repo,
        spend_checks=spend_checks,
        data_task_checks=data_task_use_cases.data_task_alert_checks,
        extra_checks=Factory(
            extra_alert_checks,
            slot_repo=repositories.service_level_slot_repo,
            heartbeat_repo=repositories.worker_heartbeat_repo,
            audit_activity_repo=repositories.audit_activity_repo,
            audit_chain_repo=repositories.audit_chain_repo,
            voice_checks=Factory(
                VoiceHealthAlertCheck,
                signal_counter=adapters.signal_counter,
                voice_activity_repo=repositories.voice_activity_repo,
            ),
            spend_checks=spend_checks,
            safety_checks=Factory(
                PlatformSafetyAlertChecks,
                job_heartbeat_repo=repositories.periodic_job_heartbeat_repo,
                reconciliation_repo=repositories.payment_reconciliation_repo,
                release=config.app_settings.provided.release_version,
            ),
            health_checks=Factory(
                PlatformHealthAlertChecks,
                signal_counter=adapters.signal_counter,
                slot_repo=repositories.service_level_slot_repo,
                maintenance_run_repo=repositories.maintenance_run_repo,
                otp_challenge_repo=repositories.otp_challenge_repo,
            ),
        ),
    )
