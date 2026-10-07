from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.factories import build_otp_delivery_facilitator
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.facilitators import OtpDeliveryFacilitatorContract
from app.facilitators.users.login_code_cap_alert_facilitator import (
    LoginCodeCapAlertFacilitator,
)
from app.facilitators.users.turnstile_bot_check_facilitator import (
    TurnstileBotCheckFacilitator,
)


class SignInFacilitatorsContainer(containers.DeclarativeContainer):
    """
    Sign-in by code: sending the codes and protecting the login from abuse.
    A child of FacilitatorsContainer, which names them flat
    (`facilitators.otp_delivery_facilitator`).
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    # Sign-in codes: Twilio SMS, Telegram Gateway, WhatsApp authentication
    # template and SMTP e-mail, each when configured; in development and test
    # the other channels write the code to the log.
    otp_delivery_facilitator: Singleton[OtpDeliveryFacilitatorContract] = Singleton(
        build_otp_delivery_facilitator,
        settings=config.app_settings,
        sms_client=clients.twilio_messaging_client,
        telegram_gateway_client=clients.telegram_gateway_client,
        whatsapp_client=clients.whatsapp_authentication_client,
        email_client=clients.smtp_email_client,
        localized_text_resolver=utilities.localized_text_resolver,
    )
    # Login abuse protection: the Turnstile check of risky code requests
    # (off without TURNSTILE_* keys) and the alert when a cap refuses sends.
    bot_check_facilitator: Singleton[TurnstileBotCheckFacilitator] = Singleton(
        TurnstileBotCheckFacilitator,
        verification_client=clients.turnstile_verification_client,
        site_key=config.app_settings.provided.turnstile_site_key,
    )
    login_code_cap_alerts: Singleton[LoginCodeCapAlertFacilitator] = Singleton(
        LoginCodeCapAlertFacilitator,
        email_client=clients.smtp_email_client,
        platform_admin_emails=config.app_settings.provided.platform_admin_emails,
        wall_clock=time_provider.microsecond_wall_clock,
        signal_counter=adapters.signal_counter,
    )
