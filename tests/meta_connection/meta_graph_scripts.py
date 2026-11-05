"""
Meta's answers to the self-serve connection, scripted on the channels
testbed's recording Graph transport (vendor-shaped, low-entropy values).
"""

from typing import Any

from tests.channels.recording_transport import RecordingTransport

META_APP_ID: str = "1234567890"
SIGNUP_CONFIG_ID: str = "987654321"
BUSINESS_TOKEN: str = "test-business-token-0000"
USER_TOKEN: str = "test-user-token-0000"
LONG_USER_TOKEN: str = "test-long-user-token-0000"
PAGE_TOKEN: str = "test-page-token-0000-0000"
WABA_ID: str = "102290129340398"
OTHER_WABA_ID: str = "102290129340399"
SIGNUP_NUMBER_ID: str = "106540352242923"
OTHER_NUMBER_ID: str = "106540352242924"
PICKED_PAGE_ID: str = "4410002"
PICKED_INSTAGRAM_ID: str = "17841400000000002"
PLAIN_PAGE_ID: str = "4410003"


def script_code_exchange(graph: RecordingTransport, token: str) -> None:
    graph.respond(
        "GET", r"/oauth/access_token$", {"access_token": token, "token_type": "bearer"}
    )


def script_grants(
    graph: RecordingTransport,
    accounts: list[str],
    scopes: tuple[str, ...] = (
        "whatsapp_business_management",
        "whatsapp_business_messaging",
    ),
) -> None:
    graph.respond(
        "GET",
        r"/debug_token$",
        {
            "data": {
                "app_id": META_APP_ID,
                "type": "SYSTEM_USER",
                "is_valid": True,
                "expires_at": 0,
                "scopes": list(scopes),
                "granular_scopes": [
                    {"scope": scope, "target_ids": accounts} for scope in scopes
                ],
            }
        },
    )


def script_numbers(
    graph: RecordingTransport, account: str, numbers: list[tuple[str, str]]
) -> None:
    graph.respond(
        "GET",
        rf"/{account}/phone_numbers$",
        {
            "data": [
                {
                    "id": number_id,
                    "display_phone_number": display,
                    "verified_name": "Funicular VR",
                }
                for number_id, display in numbers
            ]
        },
    )


def script_whatsapp_signup(graph: RecordingTransport) -> None:
    """A business token for one account with one number, accepted everywhere."""

    script_code_exchange(graph, BUSINESS_TOKEN)
    script_grants(graph, [WABA_ID])
    script_numbers(graph, WABA_ID, [(SIGNUP_NUMBER_ID, "+995 555 12-34-56")])
    graph.respond("POST", rf"/{WABA_ID}/subscribed_apps$", {"success": True})
    graph.respond("POST", rf"/{SIGNUP_NUMBER_ID}/register$", {"success": True})


def page(page_id: str, name: str, instagram: str | None = None) -> dict[str, Any]:
    entry: dict[str, Any] = {"id": page_id, "name": name, "username": name.lower()}
    if instagram is not None:
        entry["instagram_business_account"] = {"id": instagram, "username": "cafe.ig"}
    return entry


def script_pages(graph: RecordingTransport) -> None:
    """The owner's two pages; only "Funicular" has an Instagram account."""

    script_code_exchange(graph, USER_TOKEN)
    graph.respond(
        "GET",
        r"/me/accounts$",
        {
            "data": [
                page(PLAIN_PAGE_ID, "Atelier"),
                page(PICKED_PAGE_ID, "Funicular", PICKED_INSTAGRAM_ID),
            ]
        },
    )


def script_picked_page(graph: RecordingTransport) -> None:
    """The long-lived owner token, the page's token, the page and its webhook."""

    graph.respond(
        "GET",
        r"/oauth/access_token$",
        {"access_token": LONG_USER_TOKEN, "token_type": "bearer"},
    )
    # One answer for both reads of the page: its token, then its profile.
    graph.respond(
        "GET",
        rf"/{PICKED_PAGE_ID}$",
        {
            **page(PICKED_PAGE_ID, "Funicular", PICKED_INSTAGRAM_ID),
            "access_token": PAGE_TOKEN,
        },
    )
    graph.respond("POST", rf"/{PICKED_PAGE_ID}/subscribed_apps$", {"success": True})
