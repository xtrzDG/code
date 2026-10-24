"""
Seams of the login abuse protection: the bot check of risky code requests
(Cloudflare Turnstile), the alert when a platform cap refuses sends, and
the numbers a paid code is never sent to.
"""

from typing import Protocol

from app.contracts.client_contract import ClientContract
from app.contracts.facilitator_contract import FacilitatorContract
from app.contracts.registry_contract import RegistryContract
from app.schemas.dto.login_protection import LoginCodeCapAlert, TurnstileVerification
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.booleans import IsHighCostPhoneNumber
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.users.booleans import IsBotCheckPassed
from app.schemas.typings.users.constrained_strings import (
    TurnstileResponseToken,
    TurnstileSiteKey,
)


class TurnstileVerificationClientContract(ClientContract, Protocol):
    def verify(
        self,
        token: TurnstileResponseToken,
        client_ip_address: ClientIpAddress | None,
    ) -> TurnstileVerification:
        """
        Ask Cloudflare whether a widget token is valid (siteverify); every
        token can be verified once.

        Raises:
            ExternalServiceError: Cloudflare could not be asked.
        """
        raise NotImplementedError


class BotCheckFacilitatorContract(FacilitatorContract, Protocol):
    def site_key(self) -> TurnstileSiteKey | None:
        """The widget's public key; None when the bot check is off."""
        raise NotImplementedError

    def is_passed(
        self,
        token: TurnstileResponseToken,
        client_ip_address: ClientIpAddress | None,
    ) -> IsBotCheckPassed:
        """
        Whether the token proves a passed check of the login form. False,
        never an error, when Cloudflare cannot be asked (fail closed).
        """
        raise NotImplementedError


class LoginCodeCapAlertFacilitatorContract(FacilitatorContract, Protocol):
    def report_cap_reached(self, alert: LoginCodeCapAlert) -> None:
        """
        Tell the platform team a cap refused login code sends (an error
        report and an e-mail to the platform admins, at most once an hour
        per cap and country). Never raises.
        """
        raise NotImplementedError


class HighCostPhoneNumberRegistryContract(RegistryContract, Protocol):
    def is_high_cost(self, phone_number: E164PhoneNumber) -> IsHighCostPhoneNumber:
        """
        Whether a message to this number costs more than an ordinary mobile
        message (premium-rate, shared-cost, personal and universal access
        numbers, satellite and international networks, and denied ranges):
        login codes are never sent there.
        """
        raise NotImplementedError
