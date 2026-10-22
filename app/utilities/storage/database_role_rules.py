"""
What a pool's login role must not be (migration 1200,
docs/operations/deploys.md "Database roles"). The tenant pool's role
carries tenant isolation itself: it must see one business at a time
whatever a session sets, so it is a plain member of workshop_tenant and
nothing more. The platform pool's role is a member of workshop_platform
and owns nothing. A shared pool (DATABASE_URL alone) is development's
setup and has no rule here: production refuses it in the settings.
"""

from app.schemas.constants.storage import DatabasePoolKind, DatabaseRoleGroup
from app.schemas.dto.database_roles import PoolRole
from app.schemas.typings.storage.strings import DatabaseRoleProblem


def find_role_problems(pool_roles: list[PoolRole]) -> list[DatabaseRoleProblem]:
    problems: list[DatabaseRoleProblem] = []
    for pool_role in pool_roles:
        if pool_role.pool is DatabasePoolKind.TENANT:
            problems.extend(_tenant_role_problems(pool_role))
        elif pool_role.pool is DatabasePoolKind.PLATFORM:
            problems.extend(_platform_role_problems(pool_role))
    return problems


def _tenant_role_problems(pool_role: PoolRole) -> list[DatabaseRoleProblem]:
    reasons: list[str] = []
    if pool_role.is_superuser:
        reasons.append("is a superuser")
    if pool_role.bypasses_row_security:
        reasons.append("has BYPASSRLS")
    if pool_role.is_platform_member:
        reasons.append(f"is or may become {DatabaseRoleGroup.PLATFORM.value}")
    if pool_role.owns_tables:
        reasons.append("owns the tables (or may become their owner)")
    if not pool_role.is_tenant_member:
        reasons.append(f"is not a member of {DatabaseRoleGroup.TENANT.value}")
    return [_problem(pool_role, reason) for reason in reasons]


def _platform_role_problems(pool_role: PoolRole) -> list[DatabaseRoleProblem]:
    reasons: list[str] = []
    if pool_role.is_superuser:
        reasons.append("is a superuser")
    if pool_role.owns_tables:
        reasons.append("owns the tables (or may become their owner)")
    if not pool_role.is_platform_member:
        reasons.append(f"is not a member of {DatabaseRoleGroup.PLATFORM.value}")
    return [_problem(pool_role, reason) for reason in reasons]


def _problem(pool_role: PoolRole, reason: str) -> DatabaseRoleProblem:
    return DatabaseRoleProblem(
        f"the {pool_role.pool.value} pool's role {pool_role.role_name} {reason}"
    )
