"""Load-test datasets (`workshop seed-load`)."""

from typing import Protocol

from app.contracts.registry_contract import RegistryContract
from app.schemas.dto.load_data import LoadVolume, LoadVolumeRequest


class LoadDatasetRegistryContract(RegistryContract, Protocol):
    """
    The bulk history of a load business, built in memory for the moment of
    seeding: the same request and seed give the same shape (ids are new).
    Pure: nothing is stored or sent.
    """

    def build_volume(self, request: LoadVolumeRequest) -> LoadVolume:
        """Contacts, conversations with messages, bookings and visitors."""
        raise NotImplementedError
