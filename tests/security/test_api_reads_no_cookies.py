"""
The API is authenticated by bearer tokens and keys only: no route reads a
cookie, a cookie authenticates nothing, and CORS never allows credentials,
so a cross-site page cannot ride a browser's cookies into the API (the
cabinet's cookie session ends at its own proxy, which checks the origin).
"""

import ast
from pathlib import Path

from fastapi.testclient import TestClient

from tests.e2e.harness import start_workshop

HTTP_GATEWAY: Path = Path(__file__).resolve().parents[2] / "app" / "gateways" / "http"


def test_no_route_reads_a_cookie() -> None:
    readers: list[str] = []
    for source in sorted(HTTP_GATEWAY.rglob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            is_cookie_parameter = (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "Cookie"
            )
            is_cookie_read = isinstance(node, ast.Attribute) and node.attr == "cookies"
            if is_cookie_parameter or is_cookie_read:
                readers.append(f"{source.name}:{getattr(node, 'lineno', 0)}")

    assert readers == []


def test_a_cookie_authenticates_nothing_and_cors_allows_no_credentials() -> None:
    workshop = start_workshop()
    client: TestClient = workshop.client

    with_cookie = client.get(
        "/v1/businesses", headers={"Cookie": "aw_session=a-stolen-session-token"}
    )
    preflight = client.options(
        "/v1/businesses",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert with_cookie.status_code == 401
    assert "access-control-allow-credentials" not in preflight.headers
    assert preflight.headers.get("access-control-allow-origin") != (
        "https://evil.example"
    )
