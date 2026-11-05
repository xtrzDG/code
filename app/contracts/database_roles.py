"""The application's database roles, inspected at startup."""

from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.schemas.dto.database_roles import PoolRole


class DatabaseRoleInspectionAdapterContract(AdapterContract, Protocol):
    def inspect_pool_roles(self) -> list[PoolRole]:
        """
        The role each pool of the process logs in as (one entry for a
        shared pool, none without a database). ExternalServiceError when
        the database cannot be asked.
        """
        raise NotImplementedError
