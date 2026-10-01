from app.contracts.facilitators import OtpDeliveryFacilitatorContract
from app.contracts.registries import CountryRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.dto.localization import CountryProfile
from app.schemas.dto.login_options import LoginOptionsQuery, LoginOptionsView
from app.utilities.security.login_code_channels import (
    PHONE_DELIVERY_CHANNELS,
    is_sign_up_restricted,
    list_usable_phone_channels,
)


class GetLoginOptionsUseCase(UseCaseContract[LoginOptionsQuery, LoginOptionsView]):
    """
    The sign-in page asks which options work before anyone types a number:
    the login-code channels of the country (concept: the country profile
    lists SMS, WhatsApp and Telegram in its order) that have a configured
    provider, and whether e-mail sign-in works (an e-mail provider exists).
    A restricted country has no phone sign-in. Public: nothing about any
    account is returned.
    """

    def __init__(
        self,
        country_registry: CountryRegistryContract,
        otp_delivery_facilitator: OtpDeliveryFacilitatorContract,
        app_settings: AppSettings,
    ) -> None:
        self._country_registry: CountryRegistryContract = country_registry
        self._otp_delivery_facilitator: OtpDeliveryFacilitatorContract = (
            otp_delivery_facilitator
        )
        self._app_settings: AppSettings = app_settings

    def run(self, input_data: LoginOptionsQuery) -> LoginOptionsView:
        available_channels: frozenset[OtpDeliveryChannel] = (
            self._otp_delivery_facilitator.available_channels()
        )
        is_email_available: bool = OtpDeliveryChannel.EMAIL in available_channels
        if input_data.country_code is None:
            phone_channels: list[OtpDeliveryChannel] = [
                channel
                for channel in PHONE_DELIVERY_CHANNELS
                if channel in available_channels
            ]
            return LoginOptionsView(
                phone_channels=phone_channels,
                is_phone_login_available=bool(phone_channels),
                is_email_login_available=is_email_available,
            )

        country: CountryProfile = self._country_registry.get(input_data.country_code)
        if is_sign_up_restricted(country, self._app_settings):
            return LoginOptionsView(
                country_code=country.country_code,
                phone_channels=[],
                is_phone_login_available=False,
                is_email_login_available=is_email_available,
                is_sign_up_restricted=True,
            )

        usable_channels: list[OtpDeliveryChannel] = list_usable_phone_channels(
            country, available_channels
        )
        return LoginOptionsView(
            country_code=country.country_code,
            phone_channels=usable_channels,
            is_phone_login_available=bool(usable_channels),
            is_email_login_available=is_email_available,
        )
