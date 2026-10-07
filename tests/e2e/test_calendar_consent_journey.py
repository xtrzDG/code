"""
Google Calendar consent through the real application (fail-closed storage
scope): the completion learns its business only from the consent state, so
it runs platform-wide, and still connects only the owner who started it.
"""

from urllib.parse import parse_qs, urlsplit

from app.containers.app import AppContainer
from app.gateways.http.operations.google_calendar_routes import (
    GOOGLE_CALENDAR_COMPLETE_PATH,
)
from tests.e2e.harness import bearer, start_workshop
from tests.e2e.journeys import sign_in_and_create_restaurant
from tests.e2e.workshop_container import replace_provider
from tests.operations.fake_google import FakeGoogle

OTHER_OWNER_PHONE: str = "+995 555 98 76 54"


def test_the_owner_connects_google_calendar_and_a_stranger_cannot() -> None:
    google = FakeGoogle()

    def install_google(container: AppContainer) -> None:
        replace_provider(container.clients.google_calendar_client, google.client())

    workshop = start_workshop(prepare=install_google)
    with workshop.client as client:
        token, _, business_id = sign_in_and_create_restaurant(workshop)
        stranger_token, _ = workshop.sign_in_with_phone(OTHER_OWNER_PHONE)
        base = f"/v1/businesses/{business_id}/integrations/google-calendar"

        def consent_state() -> str:
            connect = client.get(f"{base}/connect-url", headers=bearer(token))
            assert connect.status_code == 200, connect.text
            query = urlsplit(str(connect.json()["authorization_url"])).query
            return parse_qs(query)["state"][0]

        hijacked = client.post(
            GOOGLE_CALENDAR_COMPLETE_PATH,
            json={"state": consent_state(), "code": "good-code"},
            headers=bearer(stranger_token),
        )
        connected = client.post(
            GOOGLE_CALENDAR_COMPLETE_PATH,
            json={"state": consent_state(), "code": "good-code"},
            headers=bearer(token),
        )
        status = client.get(base, headers=bearer(token))

    assert hijacked.status_code == 200, hijacked.text
    assert hijacked.json() == {
        "business_id": None,
        "connection": None,
        "failure": "link_expired",
    }
    assert connected.status_code == 200, connected.text
    assert connected.json()["business_id"] == business_id
    assert connected.json()["failure"] is None
    assert status.json()["is_connected"] is True
