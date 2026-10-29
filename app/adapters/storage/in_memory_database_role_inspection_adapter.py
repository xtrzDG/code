from app.contracts.database_roles import DatabaseRoleInspectionAdapterContract
from app.schemas.dto.database_roles import PoolRole


class InMemoryDatabaseRoleInspectionAdapter(DatabaseRoleInspectionAdapterContract):
    """Without DATABASE_URL there is no database role to inspect."""

    def inspect_pool_roles(self) -> list[PoolRole]:
        return []
