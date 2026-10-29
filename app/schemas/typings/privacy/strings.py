"""Keep abc order."""

from base_typed_string import BaseTypedString


class CsvCellText(BaseTypedString):
    """
    One value of an exported table as the owner reads it (a name, a local
    time, an amount); the CSV writer escapes it before it reaches a file.
    """


class CsvColumnTitle(BaseTypedString):
    """The heading of one column of an exported table, in the owner's language."""


class ExportArchivePath(BaseTypedString):
    """Where a business's export archive is kept in the export storage."""


class ExportErrorText(BaseTypedString):
    """Why building a business's export failed, for the owner and support."""


class SuppressedIdentityText(BaseTypedString):
    """
    A customer identity a suppression covers before it is hashed: an E.164
    number or a channel account id. Never stored; only its digest is.
    """


# Keep abc order for all non example types, if possible.
