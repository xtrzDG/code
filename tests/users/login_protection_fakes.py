"""Fakes of the login abuse protection: the bot check and the cap alerts."""

from app.contracts.login_protection import (
    BotCheckFacilitatorContract,
    LoginCodeCapAlertFacilitatorContract,
)
from app.schemas.dto.login_protection import LoginCodeCapAlert
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.users.booleans import IsBotCheckPassed
from app.schemas.typings.users.constrained_strings import (
    TurnstileResponseToken,
    TurnstileSiteKey,
)

TEST_SITE_KEY: TurnstileSiteKey = TurnstileSiteKey("1x00000000000000000000AA")
PASSING_TOKEN: TurnstileResponseToken = TurnstileResponseToken("passing-token")
FAILING_TOKEN: TurnstileResponseToken = TurnstileResponseToken("failing-token")


class FakeBotCheck(BotCheckFacilitatorContract):
    """
    Turnstile without Cloudflare: off until `turn_on`, then only
    `PASSING_TOKEN` passes. Records the checked tokens.
    """

    def __init__(self) -> None:
        self._site_key: TurnstileSiteKey | None = None
        self.checked_tokens: list[TurnstileResponseToken] = []
        self.checked_addresses: list[ClientIpAddress | None] = []

    def turn_on(self) -> None:
        self._site_key = TEST_SITE_KEY

    def site_key(self) -> TurnstileSiteKey | None:
        return self._site_key

    def is_passed(
        self,
        token: TurnstileResponseToken,
        client_ip_address: ClientIpAddress | None,
    ) -> IsBotCheckPassed:
        self.checked_tokens.append(token)
        self.checked_addresses.append(client_ip_address)
        return token == PASSING_TOKEN


class RecordingCapAlerts(LoginCodeCapAlertFacilitatorContract):
    """Keeps every alert instead of telling anyone."""

    def __init__(self) -> None:
        self.alerts: list[LoginCodeCapAlert] = []

    def report_cap_reached(self, alert: LoginCodeCapAlert) -> None:
        self.alerts.append(alert)
