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
from app.schemas.dto.users import (
    LoginSessionView,
    OtpChallengeView,
    StartOtpLoginCommand,
    VerifyOtpLoginCommand,
)
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessToken, RawEmailAddressInput
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
    ) -> LoginSessionView:
        challenge: OtpChallengeView = self.request_phone_code(
            raw_phone_number,
            country_hint,
        )
        return self.verify_otp_login.run(
            VerifyOtpLoginCommand(
                challenge_id=challenge.challenge_id,
                code=self.otp_delivery.last_code(),
            )
        )

    def sign_in_with_email(self, raw_email: str) -> LoginSessionView:
        challenge: OtpChallengeView = self.start_otp_login.run(
            StartOtpLoginCommand(email=RawEmailAddressInput(raw_email))
        )
        return self.verify_otp_login.run(
            VerifyOtpLoginCommand(
                challenge_id=challenge.challenge_id,
                code=self.otp_delivery.last_code(),
            )
        )

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
