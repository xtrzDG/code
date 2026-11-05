"""The places of an API process for website chat visitors' uploads."""

from contextlib import AbstractContextManager
from typing import Protocol

from app.contracts.facilitator_contract import FacilitatorContract
from app.schemas.typings.compliance.strings import ClientIpAddress


class WidgetUploadSlotsFacilitatorContract(FacilitatorContract, Protocol):
    def hold(
        self, client_ip_address: ClientIpAddress | None
    ) -> AbstractContextManager[None]:
        """
        One upload place of this process, held for the `with` block (its
        file read, checked and stored) and given back when the block ends,
        however it ends. Raises RateLimitedError at once, without waiting,
        when the process or the client network already holds its most.
        """
        raise NotImplementedError
