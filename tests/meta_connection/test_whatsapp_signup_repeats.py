"""
WhatsApp Embedded Signup over time: the owner's identity check is not asked
again when Meta's window returns, and a number keeps the two-step PIN the
platform chose for it whatever happened to the channel meanwhile.
"""

from app.contracts.session_assurance import (
    SessionAssuranceContract,
    StepUpGuardContract,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.mfa import AuthLevel
from app.schemas.dto.channels.channel_settings import DisableChannelCommand
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.typings.channels.strings import EncryptedChannelSecret
from app.schemas.typings.mfa.constrained_integers import StepUpMaxAgeSeconds
from app.use_cases.admin.security.registration_pin_resealer import (
    reseal_registration_pins,
)
from app.utilities.security.require_recent_authentication import (
    RequireRecentAuthentication,
)
from tests.foundation.access_support import signed_in
from tests.meta_connection.meta_graph_scripts import (
    OTHER_NUMBER_ID,
    SIGNUP_NUMBER_ID,
    WABA_ID,
    script_numbers,
    script_whatsapp_signup,
)
from tests.meta_connection.meta_world import MetaWorld

CODE: str = "AQB-test-code-0000-0000"
MICROSECONDS_PER_MINUTE: int = 60 * 1_000_000


class SignedInSession(SessionAssuranceContract):
    """The owner's session, as the gateway would bind it for each request."""

    def __init__(self) -> None:
        self.assurance: SessionAssurance | None = None

    def current(self) -> SessionAssurance | None:
        return self.assurance

    def bind(self, assurance: SessionAssurance) -> None:
        self.assurance = assurance


class LaterGuard(StepUpGuardContract):
    """The real step-up check, made once the world's clock exists."""

    def __init__(self) -> None:
        self.inner: StepUpGuardContract | None = None

    def require_recent_authentication(self) -> None:
        assert self.inner is not None
        self.inner.require_recent_authentication()


def register_pins(world: MetaWorld) -> list[str]:
    return [str(r.json()["pin"]) for r in world.graph.requests_to("/register")]


def signup(world: MetaWorld) -> None:
    response = world.complete({"state": world.started_state("whatsapp"), "code": CODE})
    assert response.status_code == 200, response.text


class TestStepUpOnce:
    def test_meta_window_outlasting_the_step_up_window_still_connects(self) -> None:
        session = SignedInSession()
        guard = LaterGuard()
        world = MetaWorld(step_up=guard)
        guard.inner = RequireRecentAuthentication(
            session, world.testbed.wall_clock, StepUpMaxAgeSeconds(600)
        )
        script_whatsapp_signup(world.graph)
        now = int(world.testbed.wall_clock.now_unix())
        # The owner last proved who they are nine minutes ago.
        session.bind(
            signed_in(
                world.owner_id,
                AuthLevel.TWO_FACTOR,
                now - 9 * MICROSECONDS_PER_MINUTE,
            )
        )

        start = world.start("whatsapp")
        assert start.status_code == 201, start.text
        # Choosing the account and verifying the number by SMS: two minutes.
        world.testbed.clock.advance(120)
        done = world.complete({"state": start.json()["state"], "code": CODE})

        assert done.status_code == 200, done.text
        assert done.json()["status"] == "connected"
        # The start itself still needs a recent sign-in.
        assert world.start("whatsapp").status_code == 401


class TestPinKeptPerNumber:
    def test_turning_whatsapp_off_and_on_keeps_the_number_pin(self) -> None:
        world = MetaWorld()
        script_whatsapp_signup(world.graph)
        signup(world)

        world.testbed.disable_channel.run(
            DisableChannelCommand(
                user_id=world.owner_id,
                business_id=world.business.id,
                channel=ChannelKind.WHATSAPP,
            )
        )
        signup(world)

        first, second = register_pins(world)
        assert second == first

    def test_a_number_connected_meanwhile_does_not_lose_the_first_pin(self) -> None:
        world = MetaWorld()
        script_whatsapp_signup(world.graph)
        signup(world)
        script_numbers(world.graph, WABA_ID, [(OTHER_NUMBER_ID, "+995 555 00-00-01")])
        world.graph.respond("POST", rf"/{OTHER_NUMBER_ID}/register$", {"success": True})
        signup(world)
        script_numbers(world.graph, WABA_ID, [(SIGNUP_NUMBER_ID, "+995 555 12-34-56")])
        signup(world)

        first_a, first_b, again_a = register_pins(world)
        assert again_a == first_a
        stored = world.stored(ChannelKind.WHATSAPP)
        assert [
            str(pin.phone_number_id) for pin in stored.whatsapp_registration_pins
        ] == [
            OTHER_NUMBER_ID,
            SIGNUP_NUMBER_ID,
        ]
        cipher = world.testbed.secret_cipher
        kept_b = stored.whatsapp_registration_pins[0].encrypted_pin
        assert str(cipher.decrypt(kept_b)) == first_b

    def test_every_kept_pin_is_sealed_again(self) -> None:
        world = MetaWorld()
        script_whatsapp_signup(world.graph)
        signup(world)
        before = world.stored(ChannelKind.WHATSAPP).whatsapp_registration_pins

        reseal_registration_pins(
            world.testbed.channel_repo,
            world.business.id,
            lambda sealed: EncryptedChannelSecret(f"{sealed}-again"),
        )

        after = world.stored(ChannelKind.WHATSAPP).whatsapp_registration_pins
        assert [str(pin.encrypted_pin) for pin in after] == [
            f"{before[0].encrypted_pin}-again"
        ]
        assert after[0].phone_number_id == before[0].phone_number_id
