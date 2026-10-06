"""
The server side of one SMTP session, on the wire: Python's own smtplib
talks to it through a scripted socket, so the replies are parsed (multi-line
replies, codes, capabilities) and the errors raised exactly as against a
real server, and every octet the client sends is kept for the RFC checks.
"""

import io
import re
import smtplib
import socket
import ssl
from collections.abc import Sequence
from typing import cast

from app.clients.email.smtp_email_client import SmtpConnector
from app.schemas.constants.messaging import SmtpSecurity
from app.schemas.typings.messaging.constrained_integers import SmtpPort
from app.schemas.typings.messaging.constrained_strings import SmtpHost

CRLF: bytes = b"\r\n"
END_OF_DATA: bytes = b"\r\n.\r\n"
# RFC 5321, 4.5.3.1.4 and 4.5.3.1.6 (both counting the CRLF).
MAX_COMMAND_LINE_OCTETS: int = 512
MAX_TEXT_LINE_OCTETS: int = 1000
MAIL_FROM_PATTERN: re.Pattern[bytes] = re.compile(
    rb"^mail FROM:<([^<>\s]+)>((?: [A-Za-z0-9-]+=[^\s]+)*)\r\n$", re.IGNORECASE
)


class ReplyStream(io.BytesIO):
    """The replies; smtplib closing its reader leaves the rest readable."""

    def close(self) -> None:
        return None


class ScriptedSmtpServer:
    """Answers each command with the next scripted reply and keeps the commands."""

    def __init__(self, replies: Sequence[str]) -> None:
        self._replies: ReplyStream = ReplyStream("".join(replies).encode("utf-8"))
        self.chunks: list[bytes] = []
        self.opened: list[SmtpSecurity] = []

    def sendall(self, data: bytes) -> None:
        self.chunks.append(data)

    def makefile(self, mode: str) -> ReplyStream:
        assert mode == "rb"
        return self._replies

    def close(self) -> None:
        return None

    def connector(self) -> SmtpConnector:
        def connect(
            host: SmtpHost,
            port: SmtpPort,
            security: SmtpSecurity,
            tls_context: ssl.SSLContext,
        ) -> smtplib.SMTP:
            self.opened.append(security)
            # No host: nothing is dialled; the scripted socket stands in.
            session = smtplib.SMTP(local_hostname="client.workshop.example")
            session.sock = cast(socket.socket, self)
            return session

        return connect

    def unread(self) -> bytes:
        """Replies the client never asked for (empty when the script fits)."""

        return self._replies.read()

    def commands(self) -> list[bytes]:
        """Every command line (the message itself left out)."""

        return [chunk for chunk in self.chunks if not chunk.endswith(END_OF_DATA)]

    def verbs(self) -> list[str]:
        return [
            chunk.split(b" ", 1)[0].strip().decode("ascii").upper()
            for chunk in self.commands()
        ]

    def data(self) -> bytes:
        """The message as sent between DATA and the final dot (still stuffed)."""

        [message] = [chunk for chunk in self.chunks if chunk.endswith(END_OF_DATA)]
        return message[: -len(END_OF_DATA)] + CRLF


def unstuffed(data: bytes) -> bytes:
    """RFC 5321, 4.5.2: the receiver drops the first dot of a line."""

    return CRLF.join(
        line[1:] if line.startswith(b".") else line for line in data.split(CRLF)
    )
