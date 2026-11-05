import logging

from app.contracts.login_protection import (
    BotCheckFacilitatorContract,
    TurnstileVerificationClientContract,
)
from app.schemas.dto.login_protection import TurnstileVerification
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.users.booleans import IsBotCheckPassed
from app.schemas.typings.users.constrained_strings import (
    TurnstileAction,
    TurnstileResponseToken,
    TurnstileSiteKey,
)

logger: logging.Logger = logging.getLogger(__name__)
# The cabinet's sign-in page renders the widget with this action.
LOGIN_ACTION: TurnstileAction = TurnstileAction("login")


class TurnstileBotCheckFacilitator(BotCheckFacilitatorContract):
    """
    The bot check of risky login code requests with Cloudflare Turnstile.

    Off (no site key) unless TURNSTILE_SITE_KEY and TURNSTILE_SECRET_KEY are
    set. A token passes when siteverify accepts it for the login action. When
    Cloudflare cannot be asked the check fails closed: a risky request is
    refused, the visitor may retry, and the error is logged.
    """

    def __init__(
        self,
        verification_client: TurnstileVerificationClientContract | None,
        site_key: TurnstileSiteKey | None,
    ) -> None:
        self._verification_client: TurnstileVerificationClientContract | None = (
            verification_client
        )
        self._site_key: TurnstileSiteKey | None = site_key

    def site_key(self) -> TurnstileSiteKey | None:
        if self._verification_client is None:
            return None

        return self._site_key

    def is_passed(
        self,
        token: TurnstileResponseToken,
        client_ip_address: ClientIpAddress | None,
    ) -> IsBotCheckPassed:
        if self._verification_client is None:
            return False

        try:
            verification: TurnstileVerification = self._verification_client.verify(
                token, client_ip_address
            )
        except ExternalServiceError as error:
            logger.error("Turnstile check could not be verified: %s", error)
            return False

        if not verification.is_passed:
            logger.info(
                "Turnstile check refused: %s",
                ", ".join(str(code) for code in verification.error_codes) or "-",
            )
            return False

        if verification.action is not None and verification.action != LOGIN_ACTION:
            logger.warning(
                "Turnstile token of another action (%s) refused.",
                verification.action,
            )
            return False

        return True
