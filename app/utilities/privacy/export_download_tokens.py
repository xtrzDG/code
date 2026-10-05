"""
One-time download tokens of full business exports: 256 random bits, kept
only as their SHA-256, and the link id derived from that hash (so a download
finds its link by one read by id; nothing searchable stores the token).
"""

import hashlib
import hmac
import secrets
from uuid import UUID

from app.schemas.typings.privacy.constrained_strings import (
    BusinessExportToken,
    ExportDownloadTokenHash,
)
from app.schemas.typings.privacy.prefixed_id import ExportDownloadLinkId

TOKEN_RANDOM_BYTES: int = 32
UUID_BYTES: int = 16


def generate_download_token() -> BusinessExportToken:
    """A new URL-safe token with 256 random bits."""

    return BusinessExportToken(secrets.token_urlsafe(TOKEN_RANDOM_BYTES))


def hash_download_token(token: BusinessExportToken) -> ExportDownloadTokenHash:
    """The SHA-256 hex digest of a token, the only form that is stored."""

    return ExportDownloadTokenHash(
        hashlib.sha256(str(token).encode("utf-8")).hexdigest()
    )


def download_link_id(token_hash: ExportDownloadTokenHash) -> ExportDownloadLinkId:
    """The id of the link a token belongs to: the hash's first 16 bytes."""

    digest: bytes = bytes.fromhex(str(token_hash))
    return ExportDownloadLinkId(UUID(bytes=digest[:UUID_BYTES], version=4))


def is_same_hash(
    stored: ExportDownloadTokenHash, presented: ExportDownloadTokenHash
) -> bool:
    """Constant-time comparison of the stored hash and the presented one."""

    return hmac.compare_digest(str(stored), str(presented))
