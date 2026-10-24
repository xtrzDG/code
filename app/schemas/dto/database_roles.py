"""The database role each pool of a process logs in as (startup check)."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.storage import DatabasePoolKind
from app.schemas.typings.storage.booleans import (
    IsDatabaseSuperuser,
    IsPlatformGroupMember,
    IsRowSecurityBypassed,
    IsTableOwner,
    IsTenantGroupMember,
)
from app.schemas.typings.storage.constrained_strings import DatabaseRoleName


class PoolRole(ImmutableDTO):
    """
    The role one pool of the process logs in as, and what decides what it
    may see: superuser and BYPASSRLS skip every policy; membership of
    workshop_tenant and workshop_platform picks the policy that applies;
    a role owning the tables may change or drop them (and their policies).
    """

    pool: DatabasePoolKind
    role_name: DatabaseRoleName
    is_superuser: IsDatabaseSuperuser
    bypasses_row_security: IsRowSecurityBypassed
    is_tenant_member: IsTenantGroupMember
    is_platform_member: IsPlatformGroupMember
    owns_tables: IsTableOwner
