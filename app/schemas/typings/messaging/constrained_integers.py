"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class SmtpPort(BaseConstrainedTypedInt):
    """
    TCP port of the SMTP server (587 STARTTLS, 465 TLS, 25 plain).

    Example:
        port = SmtpPort(587)
    """

    ge = 1
    le = 65535


# Keep abc order for all non example types, if possible.
