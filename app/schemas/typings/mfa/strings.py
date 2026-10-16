"""Keep abc order."""

from base_typed_string import BaseTypedString


class RawRecoveryCodeInput(BaseTypedString):
    """
    A recovery code exactly as a person typed it (any case, with or without
    the dashes and spaces), before it is normalized.

    Example:
        typed = RawRecoveryCodeInput(" K7M2 P9QX-4HFD ")
    """


class RecoveryCodeHash(BaseTypedString):
    """Keyed hash (HMAC-SHA256, hex) of a recovery code, its only stored form."""


class SealedTotpSecret(BaseTypedString):
    """
    An authenticator secret sealed with the platform's key ring (a Fernet
    token); the only stored form of the secret.
    """


class TotpAccountLabel(BaseTypedString):
    """
    The account name an authenticator app shows next to the codes: the
    user's e-mail address or phone number.

    Example:
        label = TotpAccountLabel("owner@example.com")
    """


class TotpIssuerName(BaseTypedString):
    """
    The service name an authenticator app shows above the codes.

    Example:
        issuer = TotpIssuerName("Assistant Workshop")
    """


class TotpProvisioningUri(BaseTypedString):
    """
    The `otpauth://totp/...` address of a new authenticator (Key URI
    Format): the cabinet draws it as a QR code. It holds the secret.
    """


# Keep abc order for all non example types, if possible.
