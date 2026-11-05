"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class BusinessNameConfirmation(BaseConstrainedTypedString):
    """
    The business's name as the owner typed it to confirm closing the
    business (compared with the name, ignoring case and outer spaces).
    """

    min_length = 1
    max_length = 200


class DeletionCertificateDigest(BaseConstrainedTypedString):
    """
    The SHA-256 (hex) of a deletion certificate's facts: printed on the
    certificate, so a copy can be checked against the ledger.
    """

    min_length = 64
    max_length = 64
    pattern = r"^[0-9a-f]{64}\Z"


class DeletionCertificateFileName(BaseConstrainedTypedString):
    """The download name of a deletion certificate's PDF."""

    min_length = 5
    max_length = 120
    pattern = r"^[A-Za-z0-9._-]+\.pdf\Z"


# Keep abc order for all non example types, if possible.
