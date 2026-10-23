"""The checks `PlatformAlertChecks` takes beside its own, by alert code."""

from collections.abc import Mapping

from app.contracts.health import WorkerHeartbeatRepoContract
from app.contracts.repositories.audit_chain_repositories import (
    AuditActivityRepoContract,
    AuditChainRepoContract,
)
from app.contracts.service_levels import ServiceLevelSlotRepoContract
from app.schemas.constants.monitoring import PlatformAlertCode
from app.use_cases.admin.alerts.alert_checks import AlertCheck
from app.use_cases.admin.alerts.audit_alert_checks import AuditAlertChecks
from app.use_cases.admin.alerts.burn_rate_alert_checks import burn_rate_alert_checks
from app.use_cases.admin.alerts.pipeline_alert_checks import WorkerDownAlertCheck
from app.use_cases.admin.alerts.voice_alert_checks import VoiceHealthAlertCheck


def extra_alert_checks(
    slot_repo: ServiceLevelSlotRepoContract,
    heartbeat_repo: WorkerHeartbeatRepoContract,
    audit_activity_repo: AuditActivityRepoContract,
    audit_chain_repo: AuditChainRepoContract,
    voice_checks: VoiceHealthAlertCheck,
) -> Mapping[PlatformAlertCode, AlertCheck]:
    """
    The SLOs' burn rates (1163), WORKER_DOWN from the freshest pulse (1173),
    the audit log's anomalies and broken chains (1193) and the voice
    platform's health (W20).
    """

    return {
        **burn_rate_alert_checks(slot_repo),
        PlatformAlertCode.WORKER_DOWN: WorkerDownAlertCheck(heartbeat_repo).check,
        **AuditAlertChecks(audit_activity_repo, audit_chain_repo).checks(),
        PlatformAlertCode.VOICE_HEALTH: voice_checks.check,
    }
