"""
How long the platform waits for a provider it sends through (Meta, Telegram,
Twilio, web push, Flitt): a connection that does not open within
PROVIDER_CONNECT_TIMEOUT_SECONDS fails at once (a provider that is down
mostly refuses or drops connections), and an answer may take up to the
read budget. A hanging provider holds a worker thread for 10 s at most per
call, and its circuit breaker opens after a few of those.
"""

import httpx

PROVIDER_CONNECT_TIMEOUT_SECONDS: float = 3.0
PROVIDER_READ_TIMEOUT_SECONDS: float = 10.0


def provider_timeout(
    read_seconds: float = PROVIDER_READ_TIMEOUT_SECONDS,
) -> httpx.Timeout:
    """Connect within 3 s; read, write and wait for the pool `read_seconds`."""

    return httpx.Timeout(read_seconds, connect=PROVIDER_CONNECT_TIMEOUT_SECONDS)
