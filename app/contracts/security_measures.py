"""The security measures of the DPA's section 9, read-only."""

from typing import Protocol

from app.contracts.registry_contract import RegistryContract
from app.schemas.dto.security_measures import SecurityMeasure
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion


class SecurityMeasureRegistryContract(RegistryContract, Protocol):
    def list_measures(self) -> list[SecurityMeasure]:
        """Every measure any DPA version lists, in the order section 9 has."""
        raise NotImplementedError

    def measures_of(self, version: DpaDocumentVersion) -> list[SecurityMeasure]:
        """The measures DPA `version` lists, in section 9's order."""
        raise NotImplementedError
