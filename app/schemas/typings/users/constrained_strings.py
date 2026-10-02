"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class EmailAddress(BaseConstrainedTypedString):
    """
    Lower-cased e-mail address with a single "@" and a dotted domain.

    Internationalized domains are kept in their ASCII (punycode) form, so a
    top-level domain may also be an "xn--" label (".рф" is "xn--p1ai").

    Example:
        owner_email = EmailAddress("owner@example.com")
    """

    min_length = 6
    max_length = 254
    pattern = (
        r"^[a-z0-9._%+\-]+@[a-z0-9\-]+(\.[a-z0-9\-]+)*"
        r"\.([a-z]{2,}|xn--[a-z0-9\-]+)$"
    )


class OtpCode(BaseConstrainedTypedString):
    """
    Six-digit one-time login code.

    Example:
        code = OtpCode("042317")
    """

    min_length = 6
    max_length = 6
    pattern = r"^[0-9]{6}$"


class TurnstileAction(BaseConstrainedTypedString):
    """
    The action a Turnstile widget was rendered for; Cloudflare echoes it in
    the verification, so a token from another form is refused.

    Example:
        action = TurnstileAction("login")
    """

    min_length = 1
    max_length = 32
    pattern = r"^[A-Za-z0-9_\-]+$"


class TurnstileResponseToken(BaseConstrainedTypedString):
    """
    The one-time answer of a passed Cloudflare Turnstile check (the
    widget's `cf-turnstile-response`), opaque and at most 2048 characters.

    Example:
        token = TurnstileResponseToken("0.zrSnRHO7h0HwSjSCU8oyzbjEtD8p...")
    """

    min_length = 1
    max_length = 2048
    pattern = r"^[\x21-\x7e]+$"


class TurnstileSiteKey(BaseConstrainedTypedString):
    """
    Public key of a Cloudflare Turnstile widget (TURNSTILE_SITE_KEY); the
    cabinet renders the check with it.

    Example:
        site_key = TurnstileSiteKey("0x4AAAAAAABkMYinukE8nzY")
    """

    min_length = 1
    max_length = 64
    pattern = r"^[0-9A-Za-z_\-]+$"


# Keep abc order for all non example types, if possible.
