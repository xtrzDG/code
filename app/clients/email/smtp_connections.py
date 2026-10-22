"""
SMTP connections with split timeouts: the connection, its TLS handshake
(SMTP_SECURITY=ssl) and the server's greeting within
SMTP_CONNECT_TIMEOUT_SECONDS, then at most SMTP_READ_TIMEOUT_SECONDS for
each further answer. A mail server that is down fails a send in seconds,
and one that hangs holds a worker thread for one read budget per step.
"""

import smtplib
import ssl

SMTP_CONNECT_TIMEOUT_SECONDS: float = 3.0
SMTP_READ_TIMEOUT_SECONDS: float = 10.0


def open_smtp_connection(
    host: str,
    port: int,
    tls_context: ssl.SSLContext | None,
) -> smtplib.SMTP:
    """
    A connected client: TLS from the start when `tls_context` is given
    (SMTP_SECURITY=ssl), else plain (STARTTLS follows).
    """

    client: smtplib.SMTP = (
        smtplib.SMTP(timeout=SMTP_CONNECT_TIMEOUT_SECONDS)
        if tls_context is None
        else smtplib.SMTP_SSL(timeout=SMTP_CONNECT_TIMEOUT_SECONDS, context=tls_context)
    )
    client.connect(host, port)
    client.timeout = SMTP_READ_TIMEOUT_SECONDS
    if client.sock is not None:
        client.sock.settimeout(SMTP_READ_TIMEOUT_SECONDS)

    return client
