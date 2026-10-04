"""Fakes and an in-memory wiring of the accounts slice, shared by its tests.

Countries, languages and niches come from small fake registries; phone
numbers are parsed with the real `phonenumbers` library. Time is an
adjustable clock so expiry and retention can be tested without sleeping.
The wiring is layered: repositories, then user and business use cases,
then compliance use cases; this module adds the sign-in helpers.
"""

from collections.abc import Mapping

from fastapi.testclient import TestClient

from app.schemas.constants.niches import NicheKey
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.businesses import CreateBusinessCommand, CreateBusinessRequest
from app.schemas.dto.mfa_login import MfaRequiredView
from app.schemas.dto.users import (
    LoginSessionView,
    OtpChallengeView,
    StartOtpLoginCommand,
    VerifyOtpLoginCommand,
)
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessToken, RawEmailAddressInput
from app.utilities.security.user_agents import read_user_agent
from tests.users.accounts_clock import AdjustableClock
from tests.users.accounts_compliance_use_cases import AccountsComplianceUseCases
from tests.users.accounts_http import build_accounts_http_client
from tests.users.accounts_phones import PhonenumbersParser

# Kept importable from here for the tests of other slices.
__all__ = [
    "AccountsTestbed",
    "AdjustableClock",
    "PhonenumbersParser",
    "bearer",
    "build_accounts_testbed",
]


class AccountsTestbed(AccountsComplianceUseCases):
    """Every repository, fake and use case of the accounts slice, wired."""

    def request_phone_code(
        self,
        raw_phone_number: str,
        country_hint: str | None = None,
    ) -> OtpChallengeView:
        hint: CountryCode | None = (
            None if country_hint is None else CountryCode(country_hint)
        )
        return self.start_otp_login.run(
            StartOtpLoginCommand(
                phone_number=RawPhoneNumberInput(raw_phone_number),
                country_hint=hint,
            )
        )

    def sign_in_with_phone(
        self,
        raw_phone_number: str,
        country_hint: str | None = None,
        user_agent: str | None = None,
        client_ip: str | None = None,
    ) -> LoginSessionView:
        return self.expect_session(
            self.verify_phone_code(
                raw_phone_number, country_hint, user_agent, client_ip
            )
        )

    def verify_phone_code(
        self,
        raw_phone_number: str,
        country_hint: str | None = None,
        user_agent: str | None = None,
        client_ip: str | None = None,
    ) -> LoginSessionView | MfaRequiredView:
        """
        The login code step for a phone (a session, or the second step),
        from a browser and an address when given.
        """

        challenge: OtpChallengeView = self.request_phone_code(
            raw_phone_number,
            country_hint,
        )
        return self.verify_otp_login.run(
            VerifyOtpLoginCommand(
                challenge_id=challenge.challenge_id,
                code=self.otp_delivery.last_code(),
                user_agent=read_user_agent(user_agent),
                client_ip_address=None
                if client_ip is None
                else ClientIpAddress(client_ip),
            )
        )

    def sign_in_with_email(self, raw_email: str) -> LoginSessionView:
        return self.expect_session(self.verify_email_code(raw_email))

    def verify_email_code(self, raw_email: str) -> LoginSessionView | MfaRequiredView:
        """The login code step for an e-mail (a session, or the second step)."""

        challenge: OtpChallengeView = self.start_otp_login.run(
            StartOtpLoginCommand(email=RawEmailAddressInput(raw_email))
        )
        return self.verify_otp_login.run(
            VerifyOtpLoginCommand(
                challenge_id=challenge.challenge_id,
                code=self.otp_delivery.last_code(),
            )
        )

    @staticmethod
    def expect_session(answer: LoginSessionView | MfaRequiredView) -> LoginSessionView:
        assert isinstance(answer, LoginSessionView), "a second step was asked for"
        return answer

    def create_restaurant(
        self,
        owner_id: UserId,
        name: str = "Trattoria",
    ) -> BusinessDocument:
        view = self.create_business.run(
            CreateBusinessCommand(
                user_id=owner_id,
                details=CreateBusinessRequest(
                    name=BusinessName(name),
                    niche_key=NicheKey.RESTAURANT,
                ),
            )
        )
        business: BusinessDocument | None = self.business_repo.get(view.id)
        assert business is not None
        return business

    def build_http_client(self) -> TestClient:
        """FastAPI app with the three accounts routers over this testbed."""

        return build_accounts_http_client(self)


def build_accounts_testbed(
    environment_variables: Mapping[str, str] | None = None,
) -> AccountsTestbed:
    return AccountsTestbed(environment_variables or {})


def bearer(access_token: AccessToken) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}
