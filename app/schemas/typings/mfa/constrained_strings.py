"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class RecoveryCode(BaseConstrainedTypedString):
    """
    One single-use recovery code in its normalized form: three groups of
    four characters of an alphabet without look-alikes (about 60 bits).

    Example:
        code = RecoveryCode("k7m2-p9qx-4hfd")
    """

    min_length = 14
    max_length = 14
    pattern = r"^[a-hjkmnp-z2-9]{4}-[a-hjkmnp-z2-9]{4}-[a-hjkmnp-z2-9]{4}$"


class TotpCode(BaseConstrainedTypedString):
    """
    Six-digit code of an authenticator app (RFC 6238, 30-second steps).

    Example:
        code = TotpCode("492039")
    """

    min_length = 6
    max_length = 6
    pattern = r"^[0-9]{6}$"


class TotpSecret(BaseConstrainedTypedString):
    """
    The shared secret of an authenticator (160 random bits in base32, as
    authenticator apps take it). Shown once while setting it up, stored
    only sealed.

    Example:
        secret = TotpSecret("JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP")
    """

    min_length = 32
    max_length = 32
    pattern = r"^[A-Z2-7]{32}$"


# Keep abc order for all non example types, if possible.
