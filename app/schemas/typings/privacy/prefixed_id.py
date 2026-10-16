"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class BusinessExportId(BasePrefixedTypedId):
    """Random identifier of one full export of a business's data (a ZIP)."""

    prefix = "business_export"


class BusinessPrivacySettingsId(BasePrefixedTypedId):
    """
    Identifier of the privacy settings of one business (Settings → Privacy).

    Derived (UUID v5) from the business, so a business has one settings
    document and reading it is one read by id.
    """

    prefix = "privacy_settings"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


class ExportDownloadLinkId(BasePrefixedTypedId):
    """
    Identifier of one one-time download link of a full export.

    Derived from the SHA-256 of the link's token (a version-4-shaped UUID of
    its first 16 bytes), so a download finds its link by one read by id and
    the token itself is never stored.
    """

    prefix = "export_download_link"


class RetentionPurgeStateId(BasePrefixedTypedId):
    """
    Identifier of how far the retention purge of one business got.

    Derived (UUID v5) from the business: one state document per business.
    """

    prefix = "retention_purge"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


class SuppressionEntryId(BasePrefixedTypedId):
    """
    Identifier of one entry of a business's suppression list.

    Derived (UUID v5) from the business and the identity's digest, so the
    same customer saying STOP twice is one entry, and a check is one read
    by id.
    """

    prefix = "suppression_entry"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


# Keep abc order for all non example types, if possible.
