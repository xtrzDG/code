"""
The generic API limits answer 429 with Retry-After: per signed-in person,
stricter on exports, and per client address without a token.
"""

from tests.spend_guard.request_limit_app import TOKEN, MovingClock, build_limited_app

SIGNED_IN: dict[str, str] = {"Authorization": f"Bearer {TOKEN}"}
MINUTE: int = 60 * 1_000_000


def test_a_signed_in_person_is_held_at_the_limit_with_retry_after() -> None:
    clock = MovingClock()
    client, _ = build_limited_app(clock, per_user=3)

    answers = [client.get("/v1/me", headers=SIGNED_IN) for _ in range(4)]

    assert [answer.status_code for answer in answers] == [200, 200, 200, 429]
    refused = answers[-1]
    assert refused.json() == {
        "error": "rate_limited",
        "message": "Too many requests; wait a moment and try again.",
    }
    assert 1 <= int(refused.headers["Retry-After"]) <= 120


def test_the_limit_frees_as_the_minute_slides() -> None:
    clock = MovingClock()
    client, _ = build_limited_app(clock, per_user=3)
    for _ in range(3):
        client.get("/v1/me", headers=SIGNED_IN)

    clock.now += 2 * MINUTE

    assert client.get("/v1/me", headers=SIGNED_IN).status_code == 200


def test_exports_have_a_stricter_limit_of_their_own() -> None:
    clock = MovingClock()
    client, _ = build_limited_app(clock, per_user=3, exports=1)

    first = client.get("/v1/businesses/b/exports/bookings", headers=SIGNED_IN)
    second = client.get("/v1/businesses/b/exports/bookings", headers=SIGNED_IN)
    other = client.get("/v1/me", headers=SIGNED_IN)

    assert (first.status_code, second.status_code) == (200, 429)
    assert "Retry-After" in second.headers
    # A refused export is not counted: the person still has two requests.
    assert other.status_code == 200
    assert client.get("/v1/me", headers=SIGNED_IN).status_code == 200
    assert client.get("/v1/me", headers=SIGNED_IN).status_code == 429


def test_requests_without_a_token_are_limited_per_address() -> None:
    clock = MovingClock()
    client, other_address = build_limited_app(clock, per_address=2)

    answers = [client.get("/v1/catalog/countries") for _ in range(3)]

    assert [answer.status_code for answer in answers] == [200, 200, 429]
    assert answers[-1].json()["error"] == "rate_limited"
    assert 1 <= int(answers[-1].headers["Retry-After"]) <= 120
    assert answers[-1].headers["X-Request-ID"]
    assert other_address.get("/v1/catalog/countries").status_code == 200


def test_the_widget_preflights_and_signed_in_requests_skip_the_address_limit() -> None:
    clock = MovingClock()
    client, _ = build_limited_app(clock, per_user=10, per_address=1)
    client.get("/v1/catalog/countries")

    widget = [client.get("/v1/widget/b/config") for _ in range(3)]
    signed_in = client.get("/v1/me", headers=SIGNED_IN)
    preflight = client.options("/v1/catalog/countries")

    assert [answer.status_code for answer in widget] == [200, 200, 200]
    assert signed_in.status_code == 200
    assert preflight.status_code != 429
    assert client.get("/v1/catalog/countries").status_code == 429


def test_refused_tokens_count_against_the_address() -> None:
    clock = MovingClock()
    client, other_address = build_limited_app(clock, per_user=10, per_address=2)
    forged: dict[str, str] = {"Authorization": "Bearer forged-0000"}

    answers = [client.get("/v1/me", headers=forged) for _ in range(3)]

    assert [answer.status_code for answer in answers] == [401, 401, 429]
    assert "Retry-After" in answers[-1].headers
    assert client.get("/v1/catalog/countries").status_code == 429
    # A valid token still counts per person, not per address.
    assert client.get("/v1/me", headers=SIGNED_IN).status_code == 200
    assert other_address.get("/v1/me", headers=forged).status_code == 401
