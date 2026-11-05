"""
Readiness with two database roles asks both pools, and a pool whose
login role cannot be checked at startup is reported, never a crash.
"""

import pytest

from app.adapters.health.two_pool_database_probe_adapter import (
    TwoPoolDatabaseProbeAdapter,
)
from app.adapters.storage.postgres.postgres_database_role_inspection_adapter import (
    read_role_name,
)
from app.contracts.health import DatabaseProbeAdapterContract
from app.schemas.constants.observability import DatabaseProbeFailure, HealthCheckStatus
from app.schemas.constants.storage import DatabasePoolKind
from app.schemas.dto.health import DatabaseProbe
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.platform.constrained_integers import DatabasePoolSize

OK_PROBE: DatabaseProbe = DatabaseProbe(
    status=HealthCheckStatus.OK, pool_size=DatabasePoolSize(10)
)
UNREACHABLE_PROBE: DatabaseProbe = DatabaseProbe(
    status=HealthCheckStatus.FAILED,
    failure=DatabaseProbeFailure.UNREACHABLE,
    pool_size=DatabasePoolSize(4),
)


class FixedProbe(DatabaseProbeAdapterContract):
    """A pool that always answers the same, and counts how often it is asked."""

    def __init__(self, answer: DatabaseProbe) -> None:
        self._answer: DatabaseProbe = answer
        self.asked: int = 0

    def probe(self) -> DatabaseProbe:
        self.asked += 1
        return self._answer


def test_both_pools_answering_report_the_tenant_pool() -> None:
    probe = TwoPoolDatabaseProbeAdapter(
        FixedProbe(OK_PROBE), FixedProbe(OK_PROBE.model_copy())
    ).probe()

    assert probe is not None
    assert probe.status is HealthCheckStatus.OK
    assert probe.pool_size == DatabasePoolSize(10)


def test_a_failing_platform_pool_is_the_report() -> None:
    probe = TwoPoolDatabaseProbeAdapter(
        FixedProbe(OK_PROBE), FixedProbe(UNREACHABLE_PROBE)
    ).probe()

    assert probe.status is HealthCheckStatus.FAILED
    assert probe.failure is DatabaseProbeFailure.UNREACHABLE
    assert probe.pool_size == DatabasePoolSize(4)


def test_a_failing_tenant_pool_is_reported_without_asking_the_platform() -> None:
    platform = FixedProbe(OK_PROBE)

    probe = TwoPoolDatabaseProbeAdapter(FixedProbe(UNREACHABLE_PROBE), platform).probe()

    assert probe.failure is DatabaseProbeFailure.UNREACHABLE
    assert platform.asked == 0


@pytest.mark.parametrize("quoted_name", ["TenantApp", "tenant-app", "app.tenant"])
def test_a_quoted_role_name_is_reported_not_raised_as_a_crash(
    quoted_name: str,
) -> None:
    with pytest.raises(ExternalServiceError, match="tenant pool's database role"):
        read_role_name(quoted_name, DatabasePoolKind.TENANT)


def test_an_unquoted_role_name_is_read() -> None:
    assert str(read_role_name("workshop_tenant_app", DatabasePoolKind.TENANT)) == (
        "workshop_tenant_app"
    )
