"""
The harness's authenticator app: the second sign-in step of people who
have one (platform admins always do), with codes made from the API's own
clock.
"""

from dataclasses import dataclass, field

from fastapi.testclient import TestClient

from app.schemas.typings.mfa.constrained_integers import TotpTimeStep
from app.schemas.typings.mfa.constrained_strings import TotpSecret
from app.utilities.security.totp_codes import (
    TOTP_STEP_SECONDS,
    current_totp_step,
    totp_code_at,
)
from tests.e2e.edge_fakes import MovableClock
from tests.e2e.harness_settings import JsonObject


@dataclass
class HarnessAuthenticators:
    """Authenticator secrets by the phone or e-mail that signs in with them."""

    secrets: dict[str, TotpSecret] = field(default_factory=dict[str, TotpSecret])
    last_steps: dict[str, int] = field(default_factory=dict[str, int])

    def code_for(self, identity: str, clock: MovableClock) -> str:
        """
        A fresh code of this person's authenticator: a code works once, so
        the clock moves to the next 30-second step when this one is used.
        """

        step: int = int(current_totp_step(int(clock.wall_clock.now_unix())))
        if step <= self.last_steps.get(identity, -1):
            clock.advance(TOTP_STEP_SECONDS)
            step = int(current_totp_step(int(clock.wall_clock.now_unix())))
        self.last_steps[identity] = step
        return str(totp_code_at(self.secrets[identity], TotpTimeStep(step)))

    def finish_sign_in(
        self,
        client: TestClient,
        clock: MovableClock,
        identity: str,
        answer: JsonObject,
    ) -> JsonObject:
        """The session after the second step (setting the app up first)."""

        challenge: JsonObject = answer["mfa_challenge"]
        challenge_id: str = str(challenge["mfa_challenge_id"])
        if challenge["requires_enrollment"]:
            enrolled = client.post(
                "/v1/auth/mfa/enroll", json={"mfa_challenge_id": challenge_id}
            )
            assert enrolled.status_code == 200, enrolled.text
            self.secrets[identity] = TotpSecret(str(enrolled.json()["secret"]))

        verified = client.post(
            "/v1/auth/mfa/verify",
            json={
                "mfa_challenge_id": challenge_id,
                "code": self.code_for(identity, clock),
            },
        )
        assert verified.status_code == 200, verified.text
        session: JsonObject = verified.json()
        return session
