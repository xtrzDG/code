"""Encryption of stored credentials (concept: channel tokens encrypted)."""

from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.schemas.typings.channels.strings import ChannelSecret, EncryptedChannelSecret
from app.schemas.typings.security.booleans import IsSealedWithCurrentKey
from app.schemas.typings.security.constrained_integers import EncryptionKeyCount


class SecretCipherAdapterContract(AdapterContract, Protocol):
    def encrypt(self, secret: ChannelSecret) -> EncryptedChannelSecret:
        """Seal with the current key of the ring."""
        raise NotImplementedError

    def decrypt(self, encrypted_secret: EncryptedChannelSecret) -> ChannelSecret:
        """
        Open with any key of the ring. Raises ValidationFailedError when no
        key opens the ciphertext.
        """
        raise NotImplementedError


class SecretRotationAdapterContract(AdapterContract, Protocol):
    """Moving stored secrets to the current key of the ring."""

    def key_count(self) -> EncryptionKeyCount:
        raise NotImplementedError

    def is_current(
        self, encrypted_secret: EncryptedChannelSecret
    ) -> IsSealedWithCurrentKey:
        """True when the current key opens it (False: an older key or none)."""
        raise NotImplementedError

    def rotate(
        self, encrypted_secret: EncryptedChannelSecret
    ) -> EncryptedChannelSecret:
        """
        The same secret sealed with the current key. Raises
        ValidationFailedError when no key of the ring opens it.
        """
        raise NotImplementedError
