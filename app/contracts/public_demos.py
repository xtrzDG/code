"""Which businesses the landing page's visitors may chat with (sandbox)."""

from collections.abc import Sequence
from typing import Protocol

from app.contracts.registry_contract import RegistryContract
from app.schemas.typings.businesses.prefixed_id import BusinessId


class PublicDemoDirectoryRegistryContract(RegistryContract, Protocol):
    """
    The demo businesses of the public site: PUBLIC_DEMO_BUSINESS_IDS, or,
    in development without it, the businesses SEED_DEMO_DATA created.
    """

    def list_business_ids(self) -> list[BusinessId]:
        """The demo businesses in the order the landing page offers them."""
        raise NotImplementedError

    def includes(self, business_id: BusinessId) -> bool:
        """Whether visitors may chat with this business."""
        raise NotImplementedError

    def adopt_seeded(self, business_ids: Sequence[BusinessId]) -> None:
        """
        Offer the development demo businesses when no demo is configured;
        configured demos always win.
        """
        raise NotImplementedError
