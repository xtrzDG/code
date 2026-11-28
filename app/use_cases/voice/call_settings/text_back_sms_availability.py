"""Whether a business's text-backs can go by SMS, and why not (Settings → Calls)."""

from app.contracts.messaging_clients import SmsMessagingClientContract
from app.contracts.registries import CountryRegistryContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.localization import SmsSenderRegistration
from app.schemas.constants.messaging import SmsUnavailableReason
from app.schemas.domain.businesses import BusinessDocument
from app.utilities.config_helpers.sms_sender import platform_sms_unavailable_reason


class TextBackSmsAvailability:
    """
    Why a business's text-backs cannot go by SMS, None when they can.

    First the business's country: where its carriers accept the business's
    texts only from a sender registered for it (a PER_BUSINESS country),
    which the platform does not offer yet, it is
    BUSINESS_REGISTRATION_REQUIRED, whatever the platform has. Such a
    business texts none of its callers by SMS, whatever the country of
    their number, only on WhatsApp, and no sender of the platform changes
    that, so the platform's passing reason must not stand in for it.
    Otherwise, without an SMS client, it is the platform's reason: its
    Twilio account waits for a sender (NO_SENDER), or there is no SMS
    provider at all (NOT_CONFIGURED). It keys on the business's country,
    as the text-back's SMS rule does (`TextBackSmsDestinations`), and on
    the client, as the text-back itself does (`RegisterMissedCallUseCase`),
    so the view and the text-backs agree. The owner's stored SMS switch is
    never changed.
    """

    def __init__(
        self,
        sms_client: SmsMessagingClientContract | None,
        app_settings: AppSettings,
        country_registry: CountryRegistryContract,
    ) -> None:
        self._is_sms_client_configured: bool = sms_client is not None
        self._app_settings: AppSettings = app_settings
        self._country_registry: CountryRegistryContract = country_registry

    def reason_for(self, business: BusinessDocument) -> SmsUnavailableReason | None:
        if (
            self._country_registry.get(business.country_code).sms_sender_registration
            is SmsSenderRegistration.PER_BUSINESS
        ):
            return SmsUnavailableReason.BUSINESS_REGISTRATION_REQUIRED

        if not self._is_sms_client_configured:
            # No client is never "available", whatever the settings say.
            return (
                platform_sms_unavailable_reason(self._app_settings)
                or SmsUnavailableReason.NOT_CONFIGURED
            )

        return None
