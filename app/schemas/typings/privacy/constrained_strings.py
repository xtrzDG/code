"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class BusinessExportDownloadPath(BaseConstrainedTypedString):
    """
    API path of the signed, expiring download of one full business export
    (GET; the token in the query is the permission).

    Example:
        path = BusinessExportDownloadPath(
            "/v1/business-exports/business_export_0b5c/download?token=AQ0F"
        )
    """

    min_length = 30
    max_length = 400
    pattern = r"^/v1/business-exports/[a-z0-9_\-]+/download\?token=[A-Za-z0-9_\-]+$"


class BusinessExportToken(BaseConstrainedTypedString):
    """
    The signed permission to download one export until it expires:
    base64url without padding of the export id, the business, the expiry
    and an HMAC-SHA256 under a key derived from ENCRYPTION_KEY.

    Example:
        token = BusinessExportToken("AQ0Ff3...")
    """

    min_length = 16
    max_length = 200
    pattern = r"^[A-Za-z0-9_\-]+$"


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
