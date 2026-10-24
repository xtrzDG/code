from app.contracts.health import DatabaseProbeAdapterContract
from app.schemas.constants.observability import HealthCheckStatus
from app.schemas.dto.health import DatabaseProbe


class TwoPoolDatabaseProbeAdapter(DatabaseProbeAdapterContract):
    """
    Readiness over both pools of a process (migration 1200): the tenant
    pool serves every business's request, the platform pool sign-in, the
    job queue, rate limits and billing, so an instance is ready only when
    both answer. The tenant pool's look (latency, migrations, pool use) is
    the report; the first pool that fails is reported instead, so a wrong
    or unreachable DATABASE_URL_PLATFORM makes the instance not ready.
    """

    def __init__(
        self,
        tenant_probe: DatabaseProbeAdapterContract,
        platform_probe: DatabaseProbeAdapterContract,
    ) -> None:
        self._tenant_probe: DatabaseProbeAdapterContract = tenant_probe
        self._platform_probe: DatabaseProbeAdapterContract = platform_probe

    def probe(self) -> DatabaseProbe:
        tenant: DatabaseProbe = self._tenant_probe.probe()
        if tenant.status is not HealthCheckStatus.OK:
            return tenant

        platform: DatabaseProbe = self._platform_probe.probe()
        if platform.status is not HealthCheckStatus.OK:
            return platform

        return tenant
