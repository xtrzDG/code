"""
Only a verified credential exempts a request from the per-address limit:
a made-up Authorization header on a route that checks no credential, or
on a path no route serves, counts like no header.
"""

from tests.spend_guard.request_limit_app import TOKEN, MovingClock, build_limited_app

MADE_UP: dict[str, str] = {"Authorization": "Bearer made-up-0000"}
SIGNED_IN: dict[str, str] = {"Authorization": f"Bearer {TOKEN}"}


def test_a_made_up_header_on_a_public_route_counts_against_the_address() -> None:
    client, other_address = build_limited_app(MovingClock(), per_address=2)

    answers = [client.get("/v1/catalog/countries", headers=MADE_UP) for _ in range(3)]

    assert [answer.status_code for answer in answers] == [200, 200, 429]
    assert answers[-1].json()["error"] == "rate_limited"
    assert "Retry-After" in answers[-1].headers
    # Without the header the address is just as spent; another is not.
    assert client.get("/v1/catalog/countries").status_code == 429
    assert other_address.get("/v1/catalog/countries", headers=MADE_UP).status_code == (
        200
    )


def test_a_header_on_a_path_no_route_serves_is_counted_too() -> None:
    client, _ = build_limited_app(MovingClock(), per_address=2)

    missing = [client.get("/v1/nowhere", headers=MADE_UP) for _ in range(2)]

    assert [answer.status_code for answer in missing] == [404, 404]
    assert client.get("/v1/catalog/countries").status_code == 429


def test_a_verified_credential_still_counts_per_person_only() -> None:
    client, _ = build_limited_app(MovingClock(), per_user=10, per_address=1)

    signed_in = [client.get("/v1/me", headers=SIGNED_IN) for _ in range(4)]

    assert [answer.status_code for answer in signed_in] == [200, 200, 200, 200]
    assert client.get("/v1/catalog/countries").status_code == 200
