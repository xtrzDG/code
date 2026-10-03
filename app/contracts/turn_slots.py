"""Places for conversation turns in one process."""

from contextlib import AbstractContextManager
from typing import Protocol

from app.contracts.registry_contract import RegistryContract


class TurnSlotRegistryContract(RegistryContract, Protocol):
    def hold(self) -> AbstractContextManager[None]:
        """
        A place for one turn for the block. Waits while every place is
        taken; raises the registry's refusal when none frees up in time.
        A turn takes its place before anything it holds for long (a
        customer's lock, its database connection), so a waiting turn
        holds nothing.
        """
        raise NotImplementedError
