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


# Keep abc order for all non example types, if possible.
