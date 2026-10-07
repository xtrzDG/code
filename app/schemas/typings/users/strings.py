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


class SessionBrowserName(BaseTypedString):
    """
    The browser a session signs in from, as its User-Agent names it
    ("Chrome", "Safari", "Firefox"); a proper name, never translated.
    """


class SessionOperatingSystem(BaseTypedString):
    """
    The operating system a session signs in from, as its User-Agent names
    it ("macOS", "Android", "iOS"); a proper name, never translated.
    """


class TurnstileErrorCode(BaseTypedString):
    """An error code Cloudflare's siteverify returned ("invalid-input-response")."""


class UserDisplayName(BaseTypedString):
    """Name the user wants to be addressed by."""


# Keep abc order for all non example types, if possible.
