"""The audit-log client address behind proxies cannot be forged by the client."""

import asyncio
from typing import Any, cast

import httpx
from fastapi import FastAPI, Request
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.gateways.http.strict_request_parsing import read_client_ip_address

FORGED_AND_REAL: str = "203.0.113.77, 198.51.100.9"


def build_application() -> FastAPI:
    application = FastAPI()

    @application.get("/whoami")
    def whoami(request: Request) -> dict[str, str | None]:
        address = read_client_ip_address(request)
        return {"ip": None if address is None else str(address)}

    return application


def recorded_address(trusted_hosts: str) -> str | None:
    # uvicorn's and httpx's ASGI type aliases differ; both speak plain ASGI.
    application: Any = ProxyHeadersMiddleware(
        cast(Any, build_application()), trusted_hosts=trusted_hosts
    )
    transport = httpx.ASGITransport(app=application, client=("10.1.2.3", 5555))

    async def call() -> str | None:
        async with httpx.AsyncClient(
            transport=transport, base_url="http://api"
        ) as client:
            response = await client.get(
                "/whoami", headers={"x-forwarded-for": FORGED_AND_REAL}
            )
            ip: str | None = response.json()["ip"]
            return ip

    return asyncio.run(call())


def test_a_trusted_proxy_range_keeps_the_hop_the_proxy_added() -> None:
    # The deployment trusts a private range: uvicorn reads X-Forwarded-For
    # from the right and stops at the first untrusted hop.
    assert recorded_address("10.0.0.0/8") == "198.51.100.9"


def test_trusting_every_hop_would_take_the_client_forged_entry() -> None:
    # Why the deployment files must not set FORWARDED_ALLOW_IPS="*".
    assert recorded_address("*") == "203.0.113.77"
