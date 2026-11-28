from enum import StrEnum


class SmtpSecurity(StrEnum):
    """How the connection to the SMTP server is protected."""

    # Plain connection upgraded with STARTTLS (port 587).
    STARTTLS = "starttls"
    # TLS from the first byte (port 465).
    SSL = "ssl"
    # No encryption: only for a local test mail server (Mailpit, MailHog).
    NONE = "none"


class SmsUnavailableReason(StrEnum):
    """
    Why a text cannot go by SMS, for the cabinet to say so. Views only:
    never stored.
    """

    # The platform has its Twilio account but no sender yet: the platform's
    # SMS number waits for the phone carriers' approval (TWILIO_FROM_NUMBER
    # and TWILIO_MESSAGING_SERVICE_SID unset).
    NO_SENDER = "no_sender"
    # No SMS provider at all.
    NOT_CONFIGURED = "not_configured"
    # The carriers of the business's country accept its texts only from a
    # sender registered for that business (US A2P 10DLC), which the platform
    # does not offer yet: none of its text-backs goes by SMS.
    BUSINESS_REGISTRATION_REQUIRED = "business_registration_required"
