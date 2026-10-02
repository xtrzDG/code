"""Google Calendar connection routes: consent, callback and completion."""

from urllib.parse import parse_qs, urlsplit

from httpx2 import Response

from app.clients.google.google_calendar_redirect import GOOGLE_CALENDAR_CALLBACK_PATH
from app.gateways.http.operations.google_calendar_routes import (
    GOOGLE_CALENDAR_CALLBACK_PATH as ROUTE_CALLBACK_PATH,
)
from app.gateways.http.operations.google_calendar_routes import (
    GOOGLE_CALENDAR_COMPLETE_PATH as COMPLETE_PATH,
)
from tests.operations.operations_api import (
    CABINET_URL,
    OWNER_TOKEN,
    STAFF_TOKEN,
    STRANGER_TOKEN,
    Api,
)


def start_consent(api: Api) -> str:
    connect = api.get("/integrations/google-calendar/connect-url", token=OWNER_TOKEN)
    assert connect.status_code == 200
    authorization_url = str(connect.json()["authorization_url"])
    return parse_qs(urlsplit(authorization_url).query)["state"][0]


def callback(api: Api, **params: str) -> Response:
    return api.client.get(ROUTE_CALLBACK_PATH, params=params, follow_redirects=False)


def complete(api: Api, token: str | None = OWNER_TOKEN, **body: str) -> Response:
    return api.client.post(
        COMPLETE_PATH,
        json=body,
        headers={} if token is None else {"Authorization": f"Bearer {token}"},
    )


def test_google_calendar_connection_routes() -> None:
    api = Api()

    assert ROUTE_CALLBACK_PATH == GOOGLE_CALENDAR_CALLBACK_PATH
    staff = api.get("/integrations/google-calendar/connect-url")
    assert staff.status_code == 403
    before = api.get("/integrations/google-calendar")
    assert before.status_code == 200
    assert before.json() == {
        "business_id": str(api.business.id),
        "is_configured": True,
        "is_connected": False,
        "calendar_id": None,
        "calendar_name": None,
        "connected_at": None,
        "last_synced_at": None,
        "last_sync_error": None,
        "last_sync_error_at": None,
    }

    denied = complete(api, error="access_denied", state=start_consent(api))
    assert denied.status_code == 200
    assert denied.json() == {
        "business_id": str(api.business.id),
        "connection": None,
        "failure": "access_denied",
    }
    unknown = complete(api)
    assert unknown.json()["business_id"] is None
    assert unknown.json()["failure"] == "link_expired"
    state = start_consent(api)
    connected = complete(api, code="good-code", state=state)
    assert connected.status_code == 200, connected.text
    assert connected.json()["business_id"] == str(api.business.id)
    assert connected.json()["failure"] is None
    assert connected.json()["connection"]["calendar_id"] == "primary"
    assert api.connection_repo.get_by_business(api.business.id) is not None
    replayed = complete(api, code="good-code", state=state)
    assert replayed.json()["failure"] == "link_expired"

    status = api.get("/integrations/google-calendar").json()
    assert status["is_connected"] is True
    assert status["calendar_id"] == "primary"
    assert status["calendar_name"] == "owner@example.com"
    assert status["connected_at"] == int(api.world.clock.now_microseconds())
    assert "token" not in str(status).lower()
    stranger = api.get("/integrations/google-calendar", token=STRANGER_TOKEN)
    assert stranger.status_code == 404

    assert (
        api.send(
            "DELETE", "/integrations/google-calendar", token=STAFF_TOKEN
        ).status_code
        == 403
    )
    disconnected = api.send(
        "DELETE", "/integrations/google-calendar", token=OWNER_TOKEN
    )
    assert (disconnected.status_code, disconnected.content) == (204, b"")
    assert api.get("/integrations/google-calendar").json()["is_connected"] is False


def test_google_calendar_callback_only_forwards_to_the_cabinet() -> None:
    api = Api()
    state = start_consent(api)

    forwarded = callback(api, code="good-code", state=state, error=" ")

    assert forwarded.status_code == 303
    assert forwarded.headers["location"] == (
        f"{CABINET_URL}/integrations/google-calendar/callback?"
        f"code=good-code&state={state}"
    )
    # Nothing was exchanged: the public URL cannot tell who brought it back.
    assert api.connection_repo.get_by_business(api.business.id) is None
    assert not any(
        request.url.host == "oauth2.googleapis.com" for request in api.google.requests
    )
    assert complete(api, code="good-code", state=state).json()["failure"] is None


def test_google_calendar_completion_is_bound_to_the_user_who_started_it() -> None:
    api = Api()
    state = start_consent(api)

    anonymous = complete(api, token=None, code="good-code", state=state)
    stranger = complete(api, token=STRANGER_TOKEN, code="good-code", state=state)

    assert anonymous.status_code == 401
    assert stranger.status_code == 200
    assert stranger.json() == {
        "business_id": None,
        "connection": None,
        "failure": "link_expired",
    }
    assert api.connection_repo.get_by_business(api.business.id) is None
    assert not any(
        request.url.host == "oauth2.googleapis.com" for request in api.google.requests
    )
    owner = complete(api, code="good-code", state=state)
    assert owner.json()["failure"] is None
    assert api.connection_repo.get_by_business(api.business.id) is not None


def test_google_calendar_callback_without_a_cabinet_address_shows_a_page() -> None:
    api = Api(cabinet_base_url=None)

    page = callback(api, code="good-code", state=start_consent(api))

    assert page.status_code == 400
    assert page.headers["content-type"].startswith("text/html")
    assert "CABINET_BASE_URL" in page.text
    assert api.connection_repo.get_by_business(api.business.id) is None
