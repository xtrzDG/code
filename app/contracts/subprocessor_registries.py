"""The platform's sub-processor list (DPA section 8), read-only."""

from typing import Protocol

from app.contracts.registry_contract import RegistryContract
from app.schemas.dto.legal import SubprocessorChange, SubprocessorEntry
from app.schemas.typings.legal.constrained_integers import SubprocessorNoticeDays
from app.schemas.typings.legal.constrained_strings import ClientModuleName
from app.schemas.typings.legal.strings import ClientModuleExclusionReason


class SubprocessorRegistryContract(RegistryContract, Protocol):
    def list_entries(self) -> list[SubprocessorEntry]:
        """Every sub-processor the list names or has announced, in table order."""
        raise NotImplementedError

    def list_changes(self) -> list[SubprocessorChange]:
        """
        Every announced addition and removal after the original list,
        earliest first (by the day it takes effect).
        """
        raise NotImplementedError

    def notice_days(self) -> SubprocessorNoticeDays:
        """How many days ahead owners are told of a change (DPA 8.3)."""
        raise NotImplementedError

    def client_modules_without_subprocessor(
        self,
    ) -> dict[ClientModuleName, ClientModuleExclusionReason]:
        """The `app/clients` packages that reach no sub-processor, and why."""
        raise NotImplementedError
