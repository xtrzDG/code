"""Encryption of stored credentials (concept: channel tokens encrypted)."""

from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.schemas.typings.channels.strings import ChannelSecret, EncryptedChannelSecret


class SecretCipherAdapterContract(AdapterContract, Protocol):
    def encrypt(self, secret: ChannelSecret) -> EncryptedChannelSecret:
        raise NotImplementedError

    def decrypt(self, encrypted_secret: EncryptedChannelSecret) -> ChannelSecret:
        """Raises ValidationFailedError when the ciphertext is invalid."""
        raise NotImplementedError
