"""Sealing of authenticator secrets with the platform's key ring."""

from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.schemas.typings.mfa.constrained_strings import TotpSecret
from app.schemas.typings.mfa.strings import SealedTotpSecret
from app.schemas.typings.security.booleans import IsSealedWithCurrentKey


class TotpSecretCipherAdapterContract(AdapterContract, Protocol):
    def seal(self, secret: TotpSecret) -> SealedTotpSecret:
        """Seal with the current key of the ring."""
        raise NotImplementedError

    def open(self, sealed_secret: SealedTotpSecret) -> TotpSecret:
        """
        Open with any key of the ring. Raises ValidationFailedError when no
        key opens it.
        """
        raise NotImplementedError

    def is_current(self, sealed_secret: SealedTotpSecret) -> IsSealedWithCurrentKey:
        """True when the current key opens it (False: an older key or none)."""
        raise NotImplementedError

    def reseal(self, sealed_secret: SealedTotpSecret) -> SealedTotpSecret:
        """
        The same secret sealed with the current key. Raises
        ValidationFailedError when no key of the ring opens it.
        """
        raise NotImplementedError
