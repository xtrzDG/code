"""The development demo catalog (SEED_DEMO_DATA)."""

from typing import Protocol

from app.contracts.registry_contract import RegistryContract
from app.schemas.dto.demo_data import (
    DemoAccounts,
    DemoActivityRequest,
    DemoBusinessActivity,
    DemoBusinessFoundation,
    DemoFoundationRequest,
)


class DemoDatasetRegistryContract(RegistryContract, Protocol):
    """
    Demo businesses with realistic texts, built fresh for the moment of
    seeding (dates are relative to it). Pure: nothing is stored or sent.
    """

    def describe_accounts(self) -> DemoAccounts:
        """The demo owner and staff member (new ids every call)."""
        raise NotImplementedError

    def build_foundations(
        self,
        request: DemoFoundationRequest,
    ) -> list[DemoBusinessFoundation]:
        """Every demo business, owned by the given owner."""
        raise NotImplementedError

    def build_activity(self, request: DemoActivityRequest) -> DemoBusinessActivity:
        """The month of activity of one stored demo business."""
        raise NotImplementedError
