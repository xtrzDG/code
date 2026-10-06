"""
SMTP as platform e-mail uses it (Amazon SES or any submission server), on
the wire through Python's smtplib: the commands stay within RFC 5321's
limits with the bare sender in MAIL FROM, the message is 7-bit (or says
BODY=8BITMIME), dot-stuffed, every line within 998 characters, with the
headers RFC 5322 requires plus Auto-Submitted (RFC 3834); the documented
replies become the errors the delivery flow relies on - a setting to fix,
a refused recipient, and a try-again for every 4xx.
"""

import re
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from typing import Any

import pytest

from app.clients.email.smtp_email_client import SmtpEmailClient
from app.schemas.constants.messaging import SmtpSecurity
from app.schemas.dto.messaging import EmailAttachment
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.messaging.constrained_integers import SmtpPort
from app.schemas.typings.messaging.constrained_strings import (
    EmailAttachmentFileName,
    EmailAttachmentMediaType,
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
from tests.contracts.contract_files import load_json_fixture
from tests.contracts.email.smtp_wire import (
    CRLF,
    MAIL_FROM_PATTERN,
    MAX_COMMAND_LINE_OCTETS,
    MAX_TEXT_LINE_OCTETS,
    ScriptedSmtpServer,
    unstuffed,
)

SESSIONS: dict[str, Any] = load_json_fixture("email", "smtp_sessions.json")
GREETINGS: dict[str, str] = SESSIONS["greetings"]
CASES: list[dict[str, Any]] = SESSIONS["cases"]
[SENT] = [case for case in CASES if case["expected"] is None]
SENDER = EmailSenderAddress("Assistant Workshop <no-reply@workshop.example>")
RECIPIENT = EmailAddress("owner@example.com")
PASSWORD: str = "test-smtp-password-0000"
MESSAGE_ID_PATTERN: re.Pattern[str] = re.compile(r"^<[^<>@\s]+@[^<>@\s]+>$")
INVOICE = EmailAttachment(
    file_name=EmailAttachmentFileName("invoice-2026-10.pdf"),
    media_type=EmailAttachmentMediaType("application/pdf"),
    content=b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\n%%EOF\n",
)
# Bodies that test the wire rules: lines that start with a dot, short
# non-ASCII lines, a line far beyond 998 characters, an attachment.
BODIES: dict[str, tuple[str, str | None, list[EmailAttachment]]] = {
    "dots": ("Your code: 042317\n.\n.well-known lines start with a dot\n", None, []),
    "cyrillic": ("Счёт готов.\n", "<p>Счёт <b>готов</b>.</p>\n", []),
    "long-georgian-line": ("ინვოისი მზადაა. " * 120 + "\n", None, []),
    "attachment": ("Your invoice is attached.\n", None, [INVOICE]),
}


def client(server: ScriptedSmtpServer, security: SmtpSecurity) -> SmtpEmailClient:
    return SmtpEmailClient(
        host=SmtpHost("email-smtp.eu-central-1.amazonaws.com"),
        port=SmtpPort(465 if security is SmtpSecurity.SSL else 587),
        security=security,
        sender=SENDER,
        username=SmtpUsername("test-smtp-user-0000"),
        password=PlatformSecret(PASSWORD),
        connector=server.connector(),
    )


def session(case: dict[str, Any]) -> ScriptedSmtpServer:
    return ScriptedSmtpServer([GREETINGS[case["greeting"]], *case["replies"]])


@pytest.mark.parametrize("body", list(BODIES), ids=list(BODIES))
def test_a_message_on_the_wire_follows_rfc_5321_and_5322(body: str) -> None:
    text, html, attachments = BODIES[body]
    server = session(SENT)

    client(server, SmtpSecurity.SSL).send_email(
        recipient=RECIPIENT,
        subject=EmailSubject("Ваш счёт за октябрь"),
        text_body=EmailBodyText(text),
        html_body=None if html is None else EmailBodyText(html),
        attachments=attachments,
    )

    assert server.verbs() == ["EHLO", "AUTH", "MAIL", "RCPT", "DATA", "QUIT"]
    assert server.unread() == b""
    for command in server.commands():
        assert command.endswith(CRLF) and command.count(CRLF) == 1
        assert len(command) <= MAX_COMMAND_LINE_OCTETS
    mail_from = MAIL_FROM_PATTERN.match(server.commands()[2])
    assert mail_from is not None
    assert mail_from.group(1) == b"no-reply@workshop.example"
    data: bytes = server.data()
    assert data.isascii() or b"BODY=8BITMIME" in mail_from.group(2).upper()
    assert all(len(line) + 2 <= MAX_TEXT_LINE_OCTETS for line in data.split(CRLF))
    assert_rfc_5322_message(unstuffed(data), text, html, attachments)


def assert_rfc_5322_message(
    raw: bytes, text: str, html: str | None, attachments: list[EmailAttachment]
) -> None:
    message = BytesParser(policy=policy.default).parsebytes(raw)
    for header in ("Date", "From", "To", "Subject", "Message-ID", "MIME-Version"):
        assert len(message.get_all(header) or []) == 1, header
    # "-0000" (UTC, RFC 5322 3.3) parses to a naive time; it must parse.
    assert parsedate_to_datetime(str(message["Date"])).year >= 2026
    assert MESSAGE_ID_PATTERN.match(str(message["Message-ID"]))
    assert str(message["Subject"]) == "Ваш счёт за октябрь"
    assert message["Auto-Submitted"] == "auto-generated"
    plain = message.get_body(("plain",))
    assert plain is not None and unix_lines(plain.get_content()) == text
    if html is not None:
        html_part = message.get_body(("html",))
        assert html_part is not None and unix_lines(html_part.get_content()) == html
    assert [
        (part.get_filename(), part.get_content()) for part in message.iter_attachments()
    ] == [(str(item.file_name), item.content) for item in attachments]


def unix_lines(text: str) -> str:
    return text.replace("\r\n", "\n")


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_documented_replies_become_delivery_errors(case: dict[str, Any]) -> None:
    server = session(case)
    smtp = client(server, SmtpSecurity(case["security"]))

    def send() -> None:
        smtp.send_email(
            recipient=RECIPIENT,
            subject=EmailSubject("Your login code"),
            text_body=EmailBodyText("Your code: 042317\n"),
            html_body=None,
        )

    if case["expected"] is None:
        send()
    else:
        with pytest.raises(ApplicationError) as raised:
            send()
        assert type(raised.value).__name__ == case["expected"]
        for private in (PASSWORD, str(RECIPIENT), "042317"):
            assert private not in str(raised.value)
    # The script fits the session: every reply was asked for.
    assert server.unread() == b""
