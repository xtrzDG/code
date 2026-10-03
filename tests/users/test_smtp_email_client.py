"""SMTP e-mail client: connection security, login, message and error mapping."""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any

import pytest

from app.clients.email.smtp_email_client import SmtpEmailClient
from app.schemas.constants.messaging import SmtpSecurity
from app.schemas.exceptions.application_errors import (
    DeliveryNotConfiguredError,
    ExternalServiceError,
    ProviderRejectedMessageError,
)
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

PASSWORD = PlatformSecret("smtp-password-secret")
SENDER = EmailSenderAddress("Assistant Workshop <no-reply@workshop.example>")
RECIPIENT = EmailAddress("owner@example.com")


class FakeSmtp(smtplib.SMTP):
    """An smtplib client that records calls instead of talking to a server."""

    def __init__(self, failure: Exception | None = None) -> None:
        super().__init__()
        self.calls: list[str] = []
        self.sent: list[EmailMessage] = []
        self.login_arguments: tuple[str, str] | None = None
        self.failure: Exception | None = failure

    def starttls(self, *args: Any, **kwargs: Any) -> tuple[int, bytes]:
        self.calls.append("starttls")
        if isinstance(self.failure, smtplib.SMTPNotSupportedError):
            raise self.failure

        return (220, b"ready")

    def login(
        self, user: str, password: str, *, initial_response_ok: bool = True
    ) -> tuple[int, bytes]:
        del initial_response_ok
        self.calls.append("login")
        self.login_arguments = (user, password)
        if isinstance(self.failure, smtplib.SMTPAuthenticationError):
            raise self.failure

        return (235, b"ok")

    def send_message(
        self, msg: Any, *args: Any, **kwargs: Any
    ) -> dict[str, tuple[int, bytes]]:
        self.calls.append("send_message")
        if self.failure is not None and not isinstance(
            self.failure,
            smtplib.SMTPAuthenticationError | smtplib.SMTPNotSupportedError,
        ):
            raise self.failure

        self.sent.append(msg)
        return {}

    def quit(self) -> tuple[int, bytes]:
        self.calls.append("quit")
        return (221, b"bye")


class Connections:
    def __init__(self, smtp: FakeSmtp) -> None:
        self.smtp: FakeSmtp = smtp
        self.opened: list[tuple[str, int, SmtpSecurity]] = []

    def connect(
        self,
        host: SmtpHost,
        port: SmtpPort,
        security: SmtpSecurity,
        tls_context: ssl.SSLContext,
    ) -> smtplib.SMTP:
        del tls_context
        self.opened.append((str(host), int(port), security))
        return self.smtp


def build_client(
    connections: Connections,
    security: SmtpSecurity = SmtpSecurity.STARTTLS,
    with_login: bool = True,
) -> SmtpEmailClient:
    return SmtpEmailClient(
        host=SmtpHost("smtp.workshop.example"),
        port=SmtpPort(587 if security is SmtpSecurity.STARTTLS else 465),
        security=security,
        sender=SENDER,
        username=SmtpUsername("mailer") if with_login else None,
        password=PASSWORD if with_login else None,
        connector=connections.connect,
    )


def send(client: SmtpEmailClient, html: bool = True) -> None:
    client.send_email(
        recipient=RECIPIENT,
        subject=EmailSubject("Ваш код входа: 042317"),
        text_body=EmailBodyText("Код: 042317"),
        html_body=EmailBodyText("<p>Код: <b>042317</b></p>") if html else None,
    )


def test_starttls_login_and_a_multipart_message() -> None:
    connections = Connections(FakeSmtp())

    send(build_client(connections))

    smtp = connections.smtp
    assert connections.opened == [("smtp.workshop.example", 587, SmtpSecurity.STARTTLS)]
    assert smtp.calls == ["starttls", "login", "send_message", "quit"]
    assert smtp.login_arguments == ("mailer", "smtp-password-secret")
    [message] = smtp.sent
    assert message["From"] == "Assistant Workshop <no-reply@workshop.example>"
    assert message["To"] == "owner@example.com"
    assert message["Subject"] == "Ваш код входа: 042317"
    assert message["Auto-Submitted"] == "auto-generated"
    assert message["Message-ID"].endswith("@workshop.example>")
    assert message.get_content_type() == "multipart/alternative"
    text_part = message.get_body(("plain",))
    html_part = message.get_body(("html",))
    assert text_part is not None and html_part is not None
    assert text_part.get_content().strip() == "Код: 042317"
    assert "<b>042317</b>" in html_part.get_content()


def test_tls_from_the_start_and_no_login() -> None:
    connections = Connections(FakeSmtp())

    send(build_client(connections, SmtpSecurity.SSL, with_login=False), html=False)

    assert connections.opened == [("smtp.workshop.example", 465, SmtpSecurity.SSL)]
    assert connections.smtp.calls == ["send_message", "quit"]
    assert connections.smtp.sent[0].get_content_type() == "text/plain"


@pytest.mark.parametrize(
    ("failure", "expected", "kind"),
    [
        (
            smtplib.SMTPAuthenticationError(535, b"bad credentials"),
            "SMTP_PASSWORD",
            DeliveryNotConfiguredError,
        ),
        (
            smtplib.SMTPNotSupportedError("no STARTTLS"),
            "SMTP_SECURITY=ssl",
            DeliveryNotConfiguredError,
        ),
        (
            smtplib.SMTPRecipientsRefused(
                {"owner@example.com": (550, b"no such user")}
            ),
            "refused the recipient",
            ProviderRejectedMessageError,
        ),
        (
            smtplib.SMTPSenderRefused(553, b"not allowed", "x"),
            "SMTP_FROM",
            DeliveryNotConfiguredError,
        ),
        (
            smtplib.SMTPServerDisconnected("gone"),
            "SMTPServerDisconnected",
            ExternalServiceError,
        ),
        (TimeoutError("timed out"), "TimeoutError", ExternalServiceError),
    ],
)
def test_failures_are_external_errors_without_secrets(
    failure: Exception,
    expected: str,
    kind: type[ExternalServiceError],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Settings to fix and refused recipients are final; the rest is retried."""

    connections = Connections(FakeSmtp(failure))

    with (
        caplog.at_level(logging.DEBUG),
        pytest.raises(ExternalServiceError, match=expected) as raised,
    ):
        send(build_client(connections))

    assert type(raised.value) is kind
    message = str(raised.value)
    assert "smtp-password-secret" not in message + caplog.text
    assert "owner@example.com" not in message
    assert "042317" not in message
    assert raised.value.__cause__ is None
    assert connections.smtp.calls[-1] == "quit"


def test_connection_failures_are_external_errors() -> None:
    def refuse(
        host: SmtpHost, port: SmtpPort, security: SmtpSecurity, context: ssl.SSLContext
    ) -> smtplib.SMTP:
        raise ConnectionRefusedError("refused")

    client = SmtpEmailClient(
        host=SmtpHost("smtp.workshop.example"),
        port=SmtpPort(587),
        security=SmtpSecurity.STARTTLS,
        sender=SENDER,
        connector=refuse,
    )

    with pytest.raises(ExternalServiceError, match="ConnectionRefusedError"):
        send(client)
