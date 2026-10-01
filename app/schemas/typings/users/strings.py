"""Keep abc order."""

from base_typed_string import BaseTypedString


class AccessToken(BaseTypedString):
    """Opaque bearer token handed to a user after login. Never stored."""


class AccessTokenHash(BaseTypedString):
    """SHA-256 hex digest of an access token, the only stored form."""


class MaskedLoginDestination(BaseTypedString):
    """
    Phone number or e-mail with most characters hidden, shown after a code is sent.

    Example:
        destination = MaskedLoginDestination("+995 *** ** ** 56")
    """


class OtpCodeHash(BaseTypedString):
    """Keyed hash of a one-time code, the only stored form."""


class RawEmailAddressInput(BaseTypedString):
    """
    E-mail address exactly as a person typed it, before normalization.

    Example:
        raw_email = RawEmailAddressInput(" Owner@Example.COM ")
    """


class UserDisplayName(BaseTypedString):
    """Name the user wants to be addressed by."""


# Keep abc order for all non example types, if possible.
