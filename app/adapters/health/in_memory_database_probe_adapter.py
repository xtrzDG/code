from app.contracts.health import DatabaseProbeAdapterContract
from app.schemas.constants.observability import HealthCheckStatus
from app.schemas.dto.health import DatabaseProbe


class InMemoryDatabaseProbeAdapter(DatabaseProbeAdapterContract):
    """Without DATABASE_URL there is no database to probe: SKIPPED."""

    def probe(self) -> DatabaseProbe:
        return DatabaseProbe(status=HealthCheckStatus.SKIPPED)
