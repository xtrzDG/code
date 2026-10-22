"""The page picker: Messenger and Instagram connected with a picked page."""

from app.schemas.constants.channels import ChannelKind
from app.schemas.typings.meta_connection.constrained_strings import (
    MetaConnectionState,
)
from app.use_cases.channels.meta_connection.meta_states import hash_state
from tests.meta_connection.meta_graph_scripts import (
    LONG_USER_TOKEN,
    PAGE_TOKEN,
    PICKED_INSTAGRAM_ID,
    PICKED_PAGE_ID,
    PLAIN_PAGE_ID,
    USER_TOKEN,
    page,
    script_pages,
    script_picked_page,
)
from tests.meta_connection.meta_world import MetaWorld

CODE: str = "AQD-test-code-0000-0000"


def listed(world: MetaWorld, scripted: bool = False) -> tuple[str, dict[str, object]]:
    if not scripted:
        script_pages(world.graph)
    state = world.started_state("pages")
    response = world.list_pages({"state": state, "code": CODE})
    assert response.status_code == 200, response.text
    return state, response.json()


class TestPageList:
    def test_pages_with_instagram_come_first_and_the_token_is_kept(self) -> None:
        world = MetaWorld()

        state, body = listed(world)

        pages = body["pages"]
        assert isinstance(pages, list)
        assert [entry["page_id"] for entry in pages] == [PICKED_PAGE_ID, PLAIN_PAGE_ID]
        assert pages[0]["has_instagram"] is True
        assert pages[0]["instagram_account_id"] == PICKED_INSTAGRAM_ID
        assert pages[1]["has_instagram"] is False
        assert "access_token" not in str(body)
        stored = world.state_repo.get(
            world.business.id, hash_state(MetaConnectionState(state))
        )
        assert stored is not None and stored.is_consumed
        assert stored.encrypted_user_token is not None
        assert world.testbed.secret_cipher.decrypt(stored.encrypted_user_token) == (
            USER_TOKEN
        )
        accounts = world.graph.requests_to("/me/accounts")[0]
        assert accounts.headers["Authorization"] == f"Bearer {USER_TOKEN}"
        assert len(accounts.url.params["appsecret_proof"]) == 64

    def test_every_page_of_a_long_list_is_read(self) -> None:
        world = MetaWorld()
        script_pages(world.graph)
        world.graph.respond_in_turn(
            "GET",
            r"/me/accounts$",
            [
                (
                    200,
                    {
                        "data": [page(PLAIN_PAGE_ID, "Atelier")],
                        "paging": {
                            "cursors": {"after": "cursor-1"},
                            "next": "https://graph.facebook.com/next",
                        },
                    },
                ),
                (200, {"data": [page(PICKED_PAGE_ID, "Funicular")]}),
            ],
        )

        _, body = listed(world, scripted=True)

        assert len(body["pages"]) == 2  # type: ignore[arg-type]
        second = world.graph.requests_to("/me/accounts")[1]
        assert second.url.params["after"] == "cursor-1"

    def test_a_used_sign_in_lists_nothing_again(self) -> None:
        world = MetaWorld()
        state, _ = listed(world)

        again = world.list_pages({"state": state, "code": CODE})

        assert again.status_code == 422
        assert len(world.graph.requests_to("/me/accounts")) == 1


class TestPickPage:
    def test_instagram_is_connected_with_the_page_token(self) -> None:
        world = MetaWorld()
        state, _ = listed(world)
        script_picked_page(world.graph)

        response = world.pick_page(
            "instagram", {"state": state, "page_id": PICKED_PAGE_ID}
        )

        assert response.status_code == 200, response.text
        assert response.json()["account_id"] == PICKED_INSTAGRAM_ID
        assert response.json()["comment_replies"] == {
            "is_on": False,
            "keywords": [],
            "reply_text": None,
        }
        channel = world.stored(ChannelKind.INSTAGRAM)
        assert channel.encrypted_secret is not None
        assert world.testbed.secret_cipher.decrypt(channel.encrypted_secret) == (
            PAGE_TOKEN
        )
        assert channel.public_profile is not None
        assert str(channel.public_profile.instagram_username) == "cafe.ig"
        extend = world.graph.requests_to("/oauth/access_token")[-1]
        assert extend.url.params["grant_type"] == "fb_exchange_token"
        assert extend.url.params["fb_exchange_token"] == USER_TOKEN
        token_read = world.graph.requests_to(f"/{PICKED_PAGE_ID}")[0]
        assert token_read.headers["Authorization"] == f"Bearer {LONG_USER_TOKEN}"
        assert world.graph.requests_to(f"/{PICKED_PAGE_ID}/subscribed_apps")
        # The sign-in ends with the connection: its token is gone.
        assert world.state_repo.list_of_business(world.business.id) == []

    def test_messenger_takes_any_page(self) -> None:
        world = MetaWorld()
        state, _ = listed(world)
        script_picked_page(world.graph)

        response = world.pick_page(
            "messenger", {"state": state, "page_id": PICKED_PAGE_ID}
        )

        assert response.status_code == 200
        assert response.json()["account_id"] == PICKED_PAGE_ID
        assert response.json()["comment_replies"] is None

    def test_refusals(self) -> None:
        world = MetaWorld()
        state, _ = listed(world)
        script_picked_page(world.graph)
        world.graph.respond(
            "GET", rf"/{PLAIN_PAGE_ID}$", {**page(PLAIN_PAGE_ID, "Atelier")}
        )

        no_token = world.pick_page(
            "messenger", {"state": state, "page_id": PLAIN_PAGE_ID}
        )
        world.graph.respond(
            "GET",
            rf"/{PLAIN_PAGE_ID}$",
            {**page(PLAIN_PAGE_ID, "Atelier"), "access_token": PAGE_TOKEN},
        )
        no_instagram = world.pick_page(
            "instagram", {"state": state, "page_id": PLAIN_PAGE_ID}
        )
        telegram = world.pick_page(
            "telegram", {"state": state, "page_id": PICKED_PAGE_ID}
        )
        staff = world.pick_page(
            "messenger", {"state": state, "page_id": PICKED_PAGE_ID}, user="staff"
        )
        unknown_state = world.pick_page(
            "messenger", {"state": "y" * 43, "page_id": PICKED_PAGE_ID}
        )

        assert no_token.json()["reasons"][0]["code"] == "meta_page_not_found"
        assert no_instagram.json()["reasons"][0]["code"] == "instagram_account_missing"
        assert telegram.status_code == 404
        assert staff.status_code == 403
        assert unknown_state.json()["reasons"][0]["code"] == "meta_link_expired"

    def test_the_kept_token_ends_with_the_sign_in(self) -> None:
        world = MetaWorld()
        state, _ = listed(world)
        script_picked_page(world.graph)
        world.testbed.clock.advance(15 * 60)

        response = world.pick_page(
            "messenger", {"state": state, "page_id": PICKED_PAGE_ID}
        )

        assert response.json()["reasons"][0]["code"] == "meta_link_expired"
        assert world.graph.requests_to(f"/{PICKED_PAGE_ID}") == []
