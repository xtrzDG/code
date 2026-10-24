from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.typings.platform.constrained_integers import DatabasePoolSize
from app.schemas.typings.platform.strings import DatabaseUrl


class DatabaseRoleSettings(ImmutableDTO):
    """
    The application's two database roles (migration 1200,
    docs/operations/deploys.md "Database roles"): the tenant pool connects
    with `tenant_url` (DATABASE_URL_TENANT, a member of workshop_tenant),
    the platform pool with `platform_url` (DATABASE_URL_PLATFORM, a member
    of workshop_platform), holding at most `platform_pool_size` connections
    (DB_PLATFORM_POOL_SIZE; the tenant pool keeps DB_POOL_SIZE). Without
    the two addresses both pools are one pool on DATABASE_URL (local
    development and tests only: production refuses to start so).
    """

    tenant_url: DatabaseUrl | None = Field(default=None, repr=False)
    platform_url: DatabaseUrl | None = Field(default=None, repr=False)
    platform_pool_size: DatabasePoolSize = DatabasePoolSize(8)
