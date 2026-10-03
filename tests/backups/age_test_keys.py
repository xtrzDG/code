"""Fresh age identities for tests (production keys come from `age-keygen`)."""

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from app.schemas.typings.backups.constrained_strings import AgeIdentity
from app.utilities.security.age.age_keys import IDENTITY_PREFIX
from app.utilities.security.age.bech32 import bech32_encode


def generate_identity() -> AgeIdentity:
    """A new random identity, as `age-keygen` prints it."""

    private_key: bytes = X25519PrivateKey.generate().private_bytes_raw()
    return AgeIdentity(bech32_encode(IDENTITY_PREFIX.lower(), private_key).upper())
