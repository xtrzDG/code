"""One-time codes that link a staff member's Telegram chat to a business."""

import hashlib
import secrets

from app.schemas.typings.channels.constrained_strings import ManagerLinkCode
from app.schemas.typings.channels.strings import ManagerLinkCodeHash

# Crockford base32: no I, L, O or U, so a code read aloud is not misheard.
LINK_CODE_ALPHABET: str = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
LINK_CODE_LENGTH: int = 10


def generate_link_code() -> ManagerLinkCode:
    """A random code with 50 bits of entropy."""

    return ManagerLinkCode(
        "".join(secrets.choice(LINK_CODE_ALPHABET) for _ in range(LINK_CODE_LENGTH))
    )


def hash_link_code(code: ManagerLinkCode) -> ManagerLinkCodeHash:
    """SHA-256 of a code; only the hash is stored."""

    return ManagerLinkCodeHash(hashlib.sha256(str(code).encode("ascii")).hexdigest())


def read_link_code(raw_code: str) -> ManagerLinkCode | None:
    """A code as typed after "/start" (any case, spaces); None if malformed."""

    normalized: str = "".join(raw_code.split()).upper()
    try:
        return ManagerLinkCode(normalized)
    except ValueError:
        return None
