"""Keep abc order."""

from base_typed_string import BaseTypedString


class EmailBodyText(BaseTypedString):
    """Body of a platform e-mail (plain text or HTML), never logged."""


class EmailSubject(BaseTypedString):
    """
    Subject line of a platform e-mail.

    Example:
        subject = EmailSubject("Your sign-in code: 042317")
    """


class SmsMessageText(BaseTypedString):
    """
    Text of a platform SMS, never logged (it may carry a login code).

    Example:
        text = SmsMessageText("042317 is your sign-in code.")
    """


class SmtpUsername(BaseTypedString):
    """Login of the SMTP server account (often an e-mail address)."""


# Keep abc order for all non example types, if possible.
