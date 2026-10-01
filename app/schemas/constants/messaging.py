from enum import StrEnum


class SmtpSecurity(StrEnum):
    """How the connection to the SMTP server is protected."""

    # Plain connection upgraded with STARTTLS (port 587).
    STARTTLS = "starttls"
    # TLS from the first byte (port 465).
    SSL = "ssl"
    # No encryption: only for a local test mail server (Mailpit, MailHog).
    NONE = "none"
