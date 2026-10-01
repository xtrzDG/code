import smtplib
import ssl
from collections.abc import Callable
from contextlib import suppress
from email.message import EmailMessage
from email.utils import formatdate, make_msgid, parseaddr

from app.contracts.messaging_clients import EmailSenderClientContract
from app.schemas.constants.messaging import SmtpSecurity
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.messaging.constrained_integers import SmtpPort
from app.schemas.typings.messaging.constrained_strings import (
    EmailSenderAddress,
    SmtpHost,
)
from app.schemas.typings.messaging.strings import (
    EmailBodyText,
    EmailSubject,
    SmtpUsername,
)
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.users.constrained_strings import EmailAddress

CONNECT_TIMEOUT_SECONDS: float = 15.0

# Opens a connection: (host, port, security, TLS context) -> connected client.
type SmtpConnector = Callable[
    [SmtpHost, SmtpPort, SmtpSecurity, ssl.SSLContext],
    smtplib.SMTP,
]


def connect_to_smtp_server(
    host: SmtpHost,
    port: SmtpPort,
    security: SmtpSecurity,
    tls_context: ssl.SSLContext,
) -> smtplib.SMTP:
    """A connected client; TLS from the start for SMTP_SECURITY=ssl."""

    if security is SmtpSecurity.SSL:
        return smtplib.SMTP_SSL(
            str(host),
            int(port),
            timeout=CONNECT_TIMEOUT_SECONDS,
            context=tls_context,
        )

    return smtplib.SMTP(str(host), int(port), timeout=CONNECT_TIMEOUT_SECONDS)


class SmtpEmailClient(EmailSenderClientContract):
    """
    Platform e-mail over SMTP (any provider: Mailgun, Postmark, SES, a
    mailbox): one connection per message, STARTTLS or TLS with certificate
    checks, optional login.

    The password is only handed to smtplib (debug output stays off); errors
    name the failure kind, never the password, the recipient or the body.
    """

    def __init__(
        self,
        host: SmtpHost,
        port: SmtpPort,
        security: SmtpSecurity,
        sender: EmailSenderAddress,
        username: SmtpUsername | None = None,
        password: PlatformSecret | None = None,
        connector: SmtpConnector = connect_to_smtp_server,
        tls_context: ssl.SSLContext | None = None,
    ) -> None:
        self._host: SmtpHost = host
        self._port: SmtpPort = port
        self._security: SmtpSecurity = security
        self._sender: EmailSenderAddress = sender
        self._username: SmtpUsername | None = username
        self._password: PlatformSecret | None = password
        self._connector: SmtpConnector = connector
        self._tls_context: ssl.SSLContext = (
            ssl.create_default_context() if tls_context is None else tls_context
        )

    def send_email(
        self,
        recipient: EmailAddress,
        subject: EmailSubject,
        text_body: EmailBodyText,
        html_body: EmailBodyText | None,
    ) -> None:
        message: EmailMessage = self._build_message(
            recipient, subject, text_body, html_body
        )
        try:
            connection: smtplib.SMTP = self._connector(
                self._host,
                self._port,
                self._security,
                self._tls_context,
            )
            try:
                if self._security is SmtpSecurity.STARTTLS:
                    connection.starttls(context=self._tls_context)

                if self._username is not None and self._password is not None:
                    connection.login(str(self._username), str(self._password))

                connection.send_message(message)
            finally:
                with suppress(smtplib.SMTPException, OSError):
                    connection.quit()
        except smtplib.SMTPAuthenticationError:
            raise ExternalServiceError(
                "The SMTP server rejected the login; check SMTP_USERNAME and "
                "SMTP_PASSWORD."
            ) from None
        except smtplib.SMTPNotSupportedError:
            raise ExternalServiceError(
                "The SMTP server does not offer STARTTLS; set SMTP_SECURITY=ssl "
                "(port 465)."
            ) from None
        except smtplib.SMTPRecipientsRefused:
            raise ExternalServiceError(
                "The SMTP server refused the recipient address."
            ) from None
        except smtplib.SMTPSenderRefused:
            raise ExternalServiceError(
                "The SMTP server refused the sender; check SMTP_FROM."
            ) from None
        except (smtplib.SMTPException, OSError) as error:
            raise ExternalServiceError(
                f"E-mail delivery failed: {type(error).__name__}."
            ) from None

    def _build_message(
        self,
        recipient: EmailAddress,
        subject: EmailSubject,
        text_body: EmailBodyText,
        html_body: EmailBodyText | None,
    ) -> EmailMessage:
        sender_address: str = parseaddr(str(self._sender))[1]
        message = EmailMessage()
        message["From"] = str(self._sender)
        message["To"] = str(recipient)
        message["Subject"] = str(subject)
        message["Date"] = formatdate(localtime=False)
        message["Message-ID"] = make_msgid(domain=sender_address.rpartition("@")[2])
        # Out-of-office robots do not answer automatic messages.
        message["Auto-Submitted"] = "auto-generated"
        message.set_content(str(text_body))
        if html_body is not None:
            message.add_alternative(str(html_body), subtype="html")

        return message
