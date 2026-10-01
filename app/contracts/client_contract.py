from typing import Protocol

from app.contracts.base_contract import BaseContract


class ClientContract(BaseContract, Protocol):
    pass
