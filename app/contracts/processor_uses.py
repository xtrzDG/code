"""The platform's flows of personal data to outside providers, read-only."""

from typing import Protocol

from app.contracts.registry_contract import RegistryContract
from app.schemas.dto.processor_uses import ProcessorUse


class ProcessorUseRegistryContract(RegistryContract, Protocol):
    def list_uses(self) -> list[ProcessorUse]:
        """Every data flow to an outside provider, with its settings and data."""
        raise NotImplementedError
