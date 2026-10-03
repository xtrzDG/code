"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class EmailSenderAddress(BaseConstrainedTypedString):
    """
    "From" of platform e-mails: an address, optionally with a display name.

    Example:
        sender = EmailSenderAddress("Assistant Workshop <no-reply@example.com>")
    """

    min_length = 3
    max_length = 320
    pattern = (
        r"^([^<>\r\n]*<[^<>@\s]+@[^<>@\s]+\.[^<>@\s]+>"
        r"|[^<>@\s]+@[^<>@\s]+\.[^<>@\s]+)$"
    )


class SmsSenderId(BaseConstrainedTypedString):
    """
    Sender of platform SMS: an E.164 number or an alphanumeric sender id
    (1 to 11 letters, digits or spaces, at least one letter).

    Example:
        sender = SmsSenderId("+12025550123")
    """

    min_length = 1
    max_length = 16
    pattern = r"^(\+[1-9][0-9]{6,14}|(?=[A-Za-z0-9 ]*[A-Za-z])[A-Za-z0-9 ]{1,11})$"


class SmtpHost(BaseConstrainedTypedString):
    """
    Host name or IP address of the SMTP server for platform e-mails.

    Example:
        host = SmtpHost("smtp.eu.mailgun.org")
    """

    min_length = 1
    max_length = 253
    pattern = r"^[A-Za-z0-9]([A-Za-z0-9.\-:\[\]]*[A-Za-z0-9\]])?$"


class TwilioAccountSid(BaseConstrainedTypedString):
    """
    Twilio account identifier ("AC" and 32 hex digits); not a secret.

    Example:
        account_sid = TwilioAccountSid("AC" + "0" * 32)
    """

    min_length = 34
    max_length = 34
    pattern = r"^AC[0-9a-fA-F]{32}$"


class TwilioMessagingServiceSid(BaseConstrainedTypedString):
    """
    Twilio Messaging Service that picks the sender ("MG" and 32 hex digits).

    Example:
        service_sid = TwilioMessagingServiceSid("MG" + "0" * 32)
    """

    min_length = 34
    max_length = 34
    pattern = r"^MG[0-9a-fA-F]{32}$"


# Keep abc order for all non example types, if possible.
