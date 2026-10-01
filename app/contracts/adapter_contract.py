from typing import Protocol

from app.contracts.base_contract import BaseContract


class AdapterContract(BaseContract, Protocol):
    pass
