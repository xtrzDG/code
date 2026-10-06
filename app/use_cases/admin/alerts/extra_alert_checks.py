"""The checks `PlatformAlertChecks` takes beside its own, by alert code."""

from collections.abc import Mapping

from app.contracts.health import WorkerHeartbeatRepoContract
from app.contracts.service_levels import ServiceLevelSlotRepoContract
from app.schemas.constants.monitoring import PlatformAlertCode
from app.use_cases.admin.alerts.alert_checks import AlertCheck
from app.use_cases.admin.alerts.burn_rate_alert_checks import burn_rate_alert_checks
from app.use_cases.admin.alerts.pipeline_alert_checks import WorkerDownAlertCheck


def extra_alert_checks(
    slot_repo: ServiceLevelSlotRepoContract,
    heartbeat_repo: WorkerHeartbeatRepoContract,
) -> Mapping[PlatformAlertCode, AlertCheck]:
    """The SLOs' burn rates (1163) and WORKER_DOWN from the freshest pulse (1173)."""

    return {
        **burn_rate_alert_checks(slot_repo),
        PlatformAlertCode.WORKER_DOWN: WorkerDownAlertCheck(heartbeat_repo).check,
    }
