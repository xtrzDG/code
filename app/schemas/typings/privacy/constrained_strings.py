"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class BusinessExportDownloadPath(BaseConstrainedTypedString):
    """
    API path of the one-time download of one full business export: opened
    with the session of the owner who asked for it (the token in the query
    is used up by the first download and expires within minutes).

    Example:
        path = BusinessExportDownloadPath(
            "/v1/business-exports/business_1f/business_export_0b5c/download?token=AQ0F"
        )
    """

    min_length = 40
    max_length = 400
    pattern = (
        r"^/v1/business-exports/[a-z0-9_\-]+/[a-z0-9_\-]+/download"
        r"\?token=[A-Za-z0-9_\-]+$"
    )


class BusinessExportToken(BaseConstrainedTypedString):
    """
    The one-time permission to download one export: 256 random bits,
    base64url (43 characters). Only its SHA-256 is stored; it works once,
    for the owner who asked for it, within EXPORT_DOWNLOAD_LINK_MINUTES.

    Example:
        token = BusinessExportToken("test-token-0000-0000")
    """

    min_length = 16
    max_length = 200
    pattern = r"^[A-Za-z0-9_\-]+$"


class ExportDownloadTokenHash(BaseConstrainedTypedString):
    """
    SHA-256 hex digest of a one-time export download token, the only form
    the token is stored in.

    Example:
        token_hash = ExportDownloadTokenHash("ab" * 32)
    """

    min_length = 64
    max_length = 64
    pattern = r"^[0-9a-f]{64}$"


class ExportFileName(BaseConstrainedTypedString):
    """
    File name a download is saved under: lowercase letters, digits, dots,
    hyphens and underscores, ending in .csv or .zip.

    Example:
        name = ExportFileName("bookings-2026-10-04.csv")
    """

    min_length = 5
    max_length = 120
    pattern = r"^[a-z0-9][a-z0-9._\-]*\.(csv|zip)$"


class SuppressionDigest(BaseConstrainedTypedString):
    """
    HMAC-SHA256 (lowercase hex) of one customer identity (an E.164 number
    or a channel account) under the platform's suppression key and the
    business: matches the identity without keeping it readable.

    Example:
        digest = SuppressionDigest("0" * 64)
    """

    min_length = 64
    max_length = 64
    pattern = r"^[0-9a-f]{64}$"


# Keep abc order for all non example types, if possible.
