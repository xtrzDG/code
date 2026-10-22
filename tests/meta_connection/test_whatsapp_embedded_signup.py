"""WhatsApp Embedded Signup: from the cabinet's sign-in to a working number."""

from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.typings.channels.strings import ChannelExternalId
from tests.meta_connection.meta_graph_scripts import (
    BUSINESS_TOKEN,
    OTHER_NUMBER_ID,
    OTHER_WABA_ID,
    SIGNUP_NUMBER_ID,
    WABA_ID,
    script_grants,
    script_numbers,
    script_whatsapp_signup,
)
from tests.meta_connection.meta_world import MetaWorld

CODE: str = "AQB-test-code-0000-0000"


def reasons(response: object) -> list[str]:
    body = getattr(response, "json")()
    return [reason["code"] for reason in body.get("reasons") or []]


class TestEmbeddedSignup:
    def test_the_number_is_connected_with_its_own_token(self) -> None:
        world = MetaWorld()
        script_whatsapp_signup(world.graph)
        state = world.started_state("whatsapp")

        response = world.complete(
            {
                "state": state,
                "code": CODE,
                "whatsapp_business_account_id": WABA_ID,
                "phone_number_id": SIGNUP_NUMBER_ID,
            }
        )

        assert response.status_code == 200, response.text
        view = response.json()
        assert view["account_id"] == SIGNUP_NUMBER_ID
        assert view["status"] == "connected"
        assert view["has_credential"] is True
        channel = world.stored(ChannelKind.WHATSAPP)
        assert channel.status is ChannelStatus.CONNECTED
        assert str(channel.whatsapp_business_account_id) == WABA_ID
        assert channel.public_profile is not None
        assert str(channel.public_profile.whatsapp_number) == "995555123456"
        cipher = world.testbed.secret_cipher
        assert channel.encrypted_secret is not None
        assert cipher.decrypt(channel.encrypted_secret) == BUSINESS_TOKEN
        assert channel.encrypted_registration_pin is not None
        pin = str(cipher.decrypt(channel.encrypted_registration_pin))
        assert len(pin) == 6 and pin.isdigit()

        exchange = world.graph.requests_to("/oauth/access_token")[0]
        assert exchange.url.params["code"] == CODE
        assert exchange.url.params["client_id"] == "1234567890"
        debug = world.graph.requests_to("/debug_token")[0]
        assert debug.url.params["input_token"] == BUSINESS_TOKEN
        assert "Bearer 1234567890|" in debug.headers["Authorization"]
        register = world.graph.requests_to("/register")[0]
        assert register.json() == {"messaging_product": "whatsapp", "pin": pin}
        assert register.headers["Authorization"] == f"Bearer {BUSINESS_TOKEN}"
        assert len(register.url.params["appsecret_proof"]) == 64
        assert world.graph.requests_to(f"/{WABA_ID}/subscribed_apps")
        assert world.testbed.audit_actions(world.business.id) == [("create", "channel")]

    def test_account_and_number_come_from_the_grants_without_hints(self) -> None:
        world = MetaWorld()
        script_whatsapp_signup(world.graph)

        response = world.complete(
            {"state": world.started_state("whatsapp"), "code": CODE}
        )

        assert response.status_code == 200, response.text
        assert response.json()["account_id"] == SIGNUP_NUMBER_ID

    def test_reconnecting_the_number_keeps_its_pin(self) -> None:
        world = MetaWorld()
        script_whatsapp_signup(world.graph)
        world.complete({"state": world.started_state("whatsapp"), "code": CODE})
        first = world.graph.requests_to("/register")[0].json()["pin"]

        world.complete({"state": world.started_state("whatsapp"), "code": CODE})

        assert world.graph.requests_to("/register")[1].json()["pin"] == first

    def test_a_number_with_its_own_pin_is_explained(self) -> None:
        world = MetaWorld()
        script_whatsapp_signup(world.graph)
        world.graph.respond(
            "POST",
            rf"/{SIGNUP_NUMBER_ID}/register$",
            {
                "error": {
                    "message": "Two step verification PIN mismatch",
                    "code": 133005,
                }
            },
            status_code=400,
        )

        response = world.complete(
            {"state": world.started_state("whatsapp"), "code": CODE}
        )

        assert response.status_code == 409
        assert reasons(response) == ["whatsapp_pin_mismatch"]
        assert (
            world.testbed.channel_repo.find_by_external_id(
                ChannelKind.WHATSAPP, ChannelExternalId(SIGNUP_NUMBER_ID)
            )
            is None
        )

    def test_missing_permissions_accounts_and_numbers(self) -> None:
        world = MetaWorld()
        script_whatsapp_signup(world.graph)
        script_grants(world.graph, [WABA_ID], scopes=("whatsapp_business_management",))
        no_messaging = world.complete(
            {"state": world.started_state("whatsapp"), "code": CODE}
        )

        script_grants(world.graph, [WABA_ID, OTHER_WABA_ID])
        two_accounts = world.complete(
            {"state": world.started_state("whatsapp"), "code": CODE}
        )

        script_grants(world.graph, [WABA_ID])
        script_numbers(
            world.graph,
            WABA_ID,
            [(SIGNUP_NUMBER_ID, "+995 555 12-34-56"), (OTHER_NUMBER_ID, "+995 1")],
        )
        two_numbers = world.complete(
            {"state": world.started_state("whatsapp"), "code": CODE}
        )
        world.graph.respond("POST", rf"/{OTHER_NUMBER_ID}/register$", {"success": True})
        named = world.complete(
            {
                "state": world.started_state("whatsapp"),
                "code": CODE,
                "phone_number_id": OTHER_NUMBER_ID,
            }
        )

        assert reasons(no_messaging) == ["meta_permission_missing"]
        assert reasons(two_accounts) == ["whatsapp_account_missing"]
        assert reasons(two_numbers) == ["whatsapp_number_missing"]
        assert named.status_code == 200
        assert named.json()["account_id"] == OTHER_NUMBER_ID
        # A number Meta does not show in the account is never registered.
        assert not world.graph.requests_to(f"/{SIGNUP_NUMBER_ID}/register")

    def test_a_number_of_another_business_is_refused(self) -> None:
        world = MetaWorld()
        script_whatsapp_signup(world.graph)
        other_owner = world.testbed.add_user("other-owner")
        other = world.testbed.add_business(other_owner, name="Other place")
        world.testbed.add_channel(
            other.id, ChannelKind.WHATSAPP, external_id=SIGNUP_NUMBER_ID
        )

        response = world.complete(
            {"state": world.started_state("whatsapp"), "code": CODE}
        )

        assert response.status_code == 409
        assert not world.graph.requests_to("/register")
