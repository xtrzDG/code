"""
age X25519 keys: the text forms of the backup keys and the raw keys.

A recipient (`age1...`) locks; its identity (`AGE-SECRET-KEY-1...`) opens.
Both are 32-byte X25519 keys in Bech32, exactly as `age-keygen` writes
them, so a backup made here opens with the `age` command line tool too.
"""

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)

from app.schemas.typings.backups.constrained_strings import AgeIdentity, AgeRecipient
from app.utilities.security.age.bech32 import (
    Bech32Error,
    bech32_decode,
    bech32_encode,
)

RECIPIENT_PREFIX: str = "age"
IDENTITY_PREFIX: str = "AGE-SECRET-KEY-"
X25519_KEY_SIZE: int = 32


class AgeKeyError(ValueError):
    """A text is not an age X25519 recipient or identity."""


def read_recipient(recipient: AgeRecipient) -> X25519PublicKey:
    """The public key of an `age1...` recipient."""

    return X25519PublicKey.from_public_bytes(
        decode_key(str(recipient), RECIPIENT_PREFIX)
    )


def read_identity(identity: AgeIdentity) -> X25519PrivateKey:
    """The private key of an `AGE-SECRET-KEY-1...` identity."""

    return X25519PrivateKey.from_private_bytes(
        decode_key(str(identity), IDENTITY_PREFIX)
    )


def recipient_of(identity: AgeIdentity) -> AgeRecipient:
    """The recipient whose backups the identity opens."""

    public_key: bytes = read_identity(identity).public_key().public_bytes_raw()
    return AgeRecipient(bech32_encode(RECIPIENT_PREFIX, public_key))


def generate_identity() -> AgeIdentity:
    """A new random identity (what `age-keygen` prints)."""

    private_key: bytes = X25519PrivateKey.generate().private_bytes_raw()
    return AgeIdentity(bech32_encode(IDENTITY_PREFIX.lower(), private_key).upper())


def decode_key(text: str, prefix: str) -> bytes:
    try:
        key: bytes = bech32_decode(text, prefix)
    except Bech32Error as error:
        raise AgeKeyError(str(error)) from error

    if len(key) != X25519_KEY_SIZE:
        raise AgeKeyError("An age X25519 key has 32 bytes.")

    return key
