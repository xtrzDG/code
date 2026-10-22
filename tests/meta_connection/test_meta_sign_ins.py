"""Starting a Facebook sign-in and the one-time state that binds it."""

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.contracts.session_assurance import StepUpGuardContract
from app.schemas.constants.meta_connection import MetaConnectionPurpose
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.exceptions.mfa_errors import StepUpRequiredError
from app.schemas.typings.meta_connection.constrained_strings import (
    MetaConnectionState,
)
from app.use_cases.channels.meta_connection.meta_states import hash_state, take_state
from tests.meta_connection.meta_graph_scripts import (
    META_APP_ID,
    SIGNUP_CONFIG_ID,
    script_whatsapp_signup,
)
from tests.meta_connection.meta_world import MetaWorld, meta_settings

CODE: str = "AQB-test-code-0000-0000"


class NotConfirmedRecently(StepUpGuardContract):
    def require_recent_authentication(self) -> None:
        raise StepUpRequiredError("Confirm it is you first.")


def reason_codes(body: dict[str, Any]) -> list[str]:
    reasons: list[dict[str, Any]] = body.get("reasons") or []
    return [str(reason["code"]) for reason in reasons]


class TestSignInOptions:
    def test_members_see_what_the_server_offers(self) -> None:
        world = MetaWorld()

        owner = world.sign_in_options().json()
        staff = world.sign_in_options("staff").json()
        stranger = world.sign_in_options("stranger")

        assert owner == {
            "whatsapp": True,
            "pages": True,
            "app_id": META_APP_ID,
            "graph_api_version": "v23.0",
        }
        assert staff == owner
        assert stranger.status_code == 404

    def test_without_the_app_or_its_signup_configuration(self) -> None:
        no_app = MetaWorld(meta_settings(META_APP_ID="")).sign_in_options().json()
        no_signup = (
            MetaWorld(meta_settings(META_EMBEDDED_SIGNUP_CONFIG_ID=""))
            .sign_in_options()
            .json()
        )

        assert no_app == {
            "whatsapp": False,
            "pages": False,
            "app_id": None,
            "graph_api_version": None,
        }
        assert no_signup["whatsapp"] is False
        assert no_signup["pages"] is True


class TestStart:
    def test_whatsapp_gets_the_signup_configuration_and_a_hashed_state(self) -> None:
        world = MetaWorld()

        response = world.start("whatsapp")

        assert response.status_code == 201
        view = response.json()
        assert view["configuration_id"] == SIGNUP_CONFIG_ID
        assert view["permissions"] == []
        assert view["app_id"] == META_APP_ID
        state = MetaConnectionState(view["state"])
        stored = world.state_repo.get(world.business.id, hash_state(state))
        assert stored is not None
        assert stored.purpose is MetaConnectionPurpose.WHATSAPP
        assert stored.user_id == world.owner_id
        assert str(state) not in stored.model_dump_json()
        assert int(stored.expires_at) - int(stored.created_at) == 15 * 60 * 1_000_000

    def test_pages_get_their_permissions(self) -> None:
        view = MetaWorld().start("pages").json()

        assert view["configuration_id"] is None
        assert "pages_messaging" in view["permissions"]
        assert "instagram_manage_comments" in view["permissions"]

    def test_only_owners_on_a_configured_server(self) -> None:
        world = MetaWorld()
        unconfigured = MetaWorld(meta_settings(META_EMBEDDED_SIGNUP_CONFIG_ID=""))

        staff = world.start("whatsapp", user="staff")
        no_signup = unconfigured.start("whatsapp")
        pages_still = unconfigured.start("pages")

        assert staff.status_code == 403
        assert no_signup.status_code == 422
        assert reason_codes(no_signup.json()) == ["meta_not_configured"]
        assert pages_still.status_code == 201

    def test_the_owner_confirms_it_is_them_before_meta_opens(self) -> None:
        world = MetaWorld(step_up=NotConfirmedRecently())

        response = world.start("whatsapp")

        assert response.status_code == 401
        assert world.state_repo.list_of_business(world.business.id) == []

    def test_ended_and_surplus_sign_ins_are_dropped(self) -> None:
        world = MetaWorld()
        first = world.started_state("pages")
        world.testbed.clock.advance(16 * 60)
        for _ in range(6):
            world.started_state("pages")

        stored = world.state_repo.list_of_business(world.business.id)

        assert len(stored) == 5
        assert (
            world.state_repo.get(
                world.business.id, hash_state(MetaConnectionState(first))
            )
            is None
        )


class TestStateUse:
    def test_a_sign_in_is_finished_once_even_at_the_same_moment(self) -> None:
        world = MetaWorld()
        script_whatsapp_signup(world.graph)
        state = world.started_state("whatsapp")
        barrier = threading.Barrier(2)

        def finish(_attempt: int) -> int:
            barrier.wait()
            return world.complete({"state": state, "code": CODE}).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = sorted(pool.map(finish, range(2)))

        assert statuses == [200, 422]
        assert len(world.graph.requests_to("/oauth/access_token")) == 1

    def test_someone_elses_ended_or_other_purpose_sign_in_is_refused(self) -> None:
        world = MetaWorld()
        script_whatsapp_signup(world.graph)
        pages_state = world.started_state("pages")
        expired = world.started_state("whatsapp")
        world.testbed.clock.advance(15 * 60)
        fresh = world.started_state("whatsapp")

        wrong_purpose = world.complete({"state": pages_state, "code": CODE})
        ended = world.complete({"state": expired, "code": CODE})
        made_up = world.complete({"state": "x" * 43, "code": CODE})
        other_user = world.complete({"state": fresh, "code": CODE}, user="staff")

        for response in (wrong_purpose, ended, made_up):
            assert response.status_code == 422
            assert reason_codes(response.json()) == ["meta_link_expired"]
        assert other_user.status_code == 403
        assert world.graph.requests_to("/oauth/access_token") == []
        # The owner's own sign-in is still usable after the refusals.
        assert world.complete({"state": fresh, "code": CODE}).status_code == 200


def test_another_owners_sign_in_is_not_theirs() -> None:
    world = MetaWorld()
    state = MetaConnectionState(world.started_state("whatsapp"))
    co_owner = world.testbed.add_user("co-owner")
    now = world.testbed.wall_clock.now_unix()

    try:
        take_state(
            world.state_repo,
            world.business.id,
            co_owner,
            state,
            MetaConnectionPurpose.WHATSAPP,
            now,
        )
    except ValidationFailedError as error:
        assert [str(reason.code) for reason in error.reasons] == ["meta_link_expired"]
    else:
        raise AssertionError("Another owner's sign-in was taken.")

    stored = world.state_repo.get(world.business.id, hash_state(state))
    assert stored is not None and not stored.is_consumed
