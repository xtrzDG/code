"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class ExportArchiveByteCount(BaseConstrainedTypedInt):
    """Size of a business's export archive (the ZIP), in bytes."""

    ge = 0


class ExportedRecordCount(BaseConstrainedTypedInt):
    """How many records (rows, documents) one export wrote."""

    ge = 0


class ExportLinkLifetimeHours(BaseConstrainedTypedInt):
    """
    How long the download link of a full business export works, in hours
    (BUSINESS_EXPORT_LINK_HOURS); the archive is deleted after it.
    """

    ge = 1
    le = 168


class SuppressedIdentityCount(BaseConstrainedTypedInt):
    """How many identities (numbers, channel accounts) a suppression covers."""

    ge = 0


# Keep abc order for all non example types, if possible.
