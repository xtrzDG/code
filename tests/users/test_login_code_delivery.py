"""Login code facilitators per channel, routing, provider selection, settings."""

import logging
from dataclasses import dataclass

import pytest

from app.containers.app import AppContainer
from app.containers.factories import (
    build_otp_delivery_facilitator,
    build_smtp_email_client,
    build_telegram_gateway_client,
    build_twilio_messaging_client,
    build_whatsapp_authentication_client,
)
from app.contracts.facilitators import OtpDeliveryFacilitatorContract
from app.contracts.messaging_clients import (
    EmailSenderClientContract,
    SmsMessagingClientContract,
    TelegramGatewayClientContract,
    WhatsAppAuthenticationClientContract,
)
from app.facilitators.users.email_otp_delivery_facilitator import (
    EmailOtpDeliveryFacilitator,
)
from app.facilitators.users.routing_otp_delivery_facilitator import (
    RoutingOtpDeliveryFacilitator,
)
from app.facilitators.users.sms_otp_delivery_facilitator import (
    SmsOtpDeliveryFacilitator,
)
from app.facilitators.users.telegram_gateway_otp_delivery_facilitator import (
    TelegramGatewayOtpDeliveryFacilitator,
)
from app.facilitators.users.whatsapp_otp_delivery_facilitator import (
    WhatsAppOtpDeliveryFacilitator,
)
from app.main import report_login_code_channels
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.constants.messaging import SmtpSecurity
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.channels.constrained_strings import (
    WhatsAppTemplateLanguageCode,
)
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.messaging.strings import (
    EmailBodyText,
    EmailSubject,
    SmsMessageText,
)
from app.schemas.typings.users.constrained_integers import OtpLifetimeSeconds
from app.schemas.typings.users.constrained_strings import EmailAddress, OtpCode
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from tests.e2e.workshop_container import replace_provider

PHONE = E164PhoneNumber("+995555123456")
EMAIL = EmailAddress("owner@example.com")
CODE = OtpCode("042317")
ALL_CHANNELS = frozenset(OtpDeliveryChannel)
TWILIO_ENVIRONMENT: dict[str, str] = {
    "TWILIO_ACCOUNT_SID": "AC" + "1f" * 16,
    "TWILIO_AUTH_TOKEN": "twilio-token",
    "TWILIO_FROM_NUMBER": "Workshop",
}
SMTP_ENVIRONMENT: dict[str, str] = {
    "SMTP_HOST": "smtp.workshop.example",
    "SMTP_FROM": "Assistant Workshop <no-reply@workshop.example>",
}
WHATSAPP_ENVIRONMENT: dict[str, str] = {
    "WHATSAPP_OTP_PHONE_NUMBER_ID": "106540352242922",
    "WHATSAPP_OTP_TEMPLATE": "login_code",
    "WHATSAPP_SYSTEM_USER_TOKEN": "system-user-token",
}


class FakeSms(SmsMessagingClientContract):
    def __init__(self) -> None:
        self.sent: list[tuple[E164PhoneNumber, SmsMessageText]] = []

    def send_sms(self, recipient: E164PhoneNumber, text: SmsMessageText) -> None:
        self.sent.append((recipient, text))


class FakeGateway(TelegramGatewayClientContract):
    def __init__(self) -> None:
        self.sent: list[tuple[E164PhoneNumber, OtpCode, OtpLifetimeSeconds]] = []

    def send_verification_message(
        self,
        phone_number: E164PhoneNumber,
        code: OtpCode,
        lifetime_seconds: OtpLifetimeSeconds,
    ) -> None:
        self.sent.append((phone_number, code, lifetime_seconds))


class FakeWhatsApp(WhatsAppAuthenticationClientContract):
    def __init__(self) -> None:
        self.sent: list[
            tuple[E164PhoneNumber, OtpCode, WhatsAppTemplateLanguageCode]
        ] = []

    def send_authentication_code(
        self,
        recipient: E164PhoneNumber,
        code: OtpCode,
        language_code: WhatsAppTemplateLanguageCode,
    ) -> None:
        self.sent.append((recipient, code, language_code))


@dataclass
class SentEmail:
    recipient: EmailAddress
    subject: EmailSubject
    text_body: EmailBodyText
    html_body: EmailBodyText | None


class FakeMailer(EmailSenderClientContract):
    def __init__(self) -> None:
        self.sent: list[SentEmail] = []

    def send_email(
        self,
        recipient: EmailAddress,
        subject: EmailSubject,
        text_body: EmailBodyText,
        html_body: EmailBodyText | None,
    ) -> None:
        self.sent.append(SentEmail(recipient, subject, text_body, html_body))


def settings(**environment: str) -> AppSettings:
    return assemble_app_settings(environment)


def deliver(
    facilitator: OtpDeliveryFacilitatorContract,
    channel: OtpDeliveryChannel,
    language: str = "en",
) -> None:
    facilitator.deliver(
        delivery_channel=channel,
        phone_number=None if channel is OtpDeliveryChannel.EMAIL else PHONE,
        email=EMAIL if channel is OtpDeliveryChannel.EMAIL else None,
        code=CODE,
        language_tag=LanguageTag(language),
    )


# The GSM 7-bit default alphabet: a text only of these fits 160 per SMS part.
GSM_7BIT_CHARACTERS: frozenset[str] = frozenset(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
)


class TestChannelFacilitators:
    @pytest.mark.parametrize(
        ("language", "expected_start"),
        [
            ("ka", "Assistant Workshop: შესვლის კოდი 042317, 10 წთ."),
            ("ru-RU", "Assistant Workshop: код входа 042317, 10 мин."),
            ("pt-BR", "Assistant Workshop sign-in code: 042317. Valid for 10 min."),
        ],
    )
    def test_sms_text_is_localized_with_english_fallback(
        self, language: str, expected_start: str
    ) -> None:
        sms = FakeSms()
        facilitator = SmsOtpDeliveryFacilitator(
            sms, LocalizedTextResolver(), settings()
        )

        deliver(facilitator, OtpDeliveryChannel.SMS, language)

        [(recipient, text)] = sms.sent
        assert recipient == PHONE
        assert str(text).startswith(expected_start)
        assert facilitator.available_channels() == {OtpDeliveryChannel.SMS}

    @pytest.mark.parametrize(
        "language", ["en", "ru", "ka", "uk", "tr", "he", "ar", "de", "fr", "es"]
    )
    def test_sms_names_the_service_and_fits_one_part(self, language: str) -> None:
        sms = FakeSms()
        facilitator = SmsOtpDeliveryFacilitator(
            sms, LocalizedTextResolver(), settings(OTP_LIFETIME_SECONDS="3600")
        )

        deliver(facilitator, OtpDeliveryChannel.SMS, language)

        text = str(sms.sent[0][1])
        assert "Assistant Workshop" in text
        assert len(text) <= (160 if set(text) <= GSM_7BIT_CHARACTERS else 70)

    def test_sms_minutes_round_up(self) -> None:
        sms = FakeSms()
        facilitator = SmsOtpDeliveryFacilitator(
            sms, LocalizedTextResolver(), settings(OTP_LIFETIME_SECONDS="90")
        )

        deliver(facilitator, OtpDeliveryChannel.SMS)

        assert "Valid for 2 min." in str(sms.sent[0][1])

    @pytest.mark.parametrize(
        ("language", "subject", "body_fragment"),
        [
            ("en", "Your sign-in code: 042317", "valid for 10 minutes"),
            ("ru", "Ваш код входа: 042317", "действует 10 мин"),
            ("ka", "თქვენი შესვლის კოდი: 042317", "მოქმედებს 10 წუთის"),
            ("he", "קוד הכניסה שלך: 042317", "בתוקף 10 דקות"),
            ("hy", "Your sign-in code: 042317", "valid for 10 minutes"),
        ],
    )
    def test_email_is_localized_in_text_and_html(
        self, language: str, subject: str, body_fragment: str
    ) -> None:
        mailer = FakeMailer()
        facilitator = EmailOtpDeliveryFacilitator(
            mailer, LocalizedTextResolver(), settings()
        )

        deliver(facilitator, OtpDeliveryChannel.EMAIL, language)

        [email] = mailer.sent
        assert email.recipient == EMAIL
        assert email.subject == subject
        assert body_fragment in str(email.text_body).lower()
        assert "\n\n042317\n\n" in str(email.text_body)
        assert email.html_body is not None
        assert 'dir="auto"' in str(email.html_body)
        assert "letter-spacing:6px" in str(email.html_body)
        assert "{code}" not in str(email.html_body) + str(email.text_body)

    def test_telegram_gateway_gets_the_code_lifetime(self) -> None:
        gateway = FakeGateway()
        facilitator = TelegramGatewayOtpDeliveryFacilitator(
            gateway, settings(OTP_LIFETIME_SECONDS="300")
        )

        deliver(facilitator, OtpDeliveryChannel.TELEGRAM, "ka")

        assert gateway.sent == [(PHONE, CODE, OtpLifetimeSeconds(300))]

    @pytest.mark.parametrize(
        ("language", "expected_template_language"),
        [
            ("ru-RU", "ru"),
            ("pt", "pt_BR"),
            ("pt-BR", "pt_BR"),
            ("ka", "en"),
            ("en-GB", "en"),
        ],
    )
    def test_whatsapp_template_language_falls_back_to_the_first(
        self, language: str, expected_template_language: str
    ) -> None:
        whatsapp = FakeWhatsApp()
        facilitator = WhatsAppOtpDeliveryFacilitator(
            whatsapp,
            [
                WhatsAppTemplateLanguageCode("en"),
                WhatsAppTemplateLanguageCode("ru"),
                WhatsAppTemplateLanguageCode("pt_BR"),
            ],
        )

        deliver(facilitator, OtpDeliveryChannel.WHATSAPP, language)

        assert whatsapp.sent == [(PHONE, CODE, expected_template_language)]

    def test_providers_refuse_other_channels(self) -> None:
        facilitator = SmsOtpDeliveryFacilitator(
            FakeSms(), LocalizedTextResolver(), settings()
        )

        with pytest.raises(ExternalServiceError):
            deliver(facilitator, OtpDeliveryChannel.EMAIL)


class TestRouting:
    def test_each_channel_goes_to_its_provider(self) -> None:
        sms, mailer = FakeSms(), FakeMailer()
        routing = RoutingOtpDeliveryFacilitator(
            {
                OtpDeliveryChannel.SMS: SmsOtpDeliveryFacilitator(
                    sms, LocalizedTextResolver(), settings()
                ),
                OtpDeliveryChannel.EMAIL: EmailOtpDeliveryFacilitator(
                    mailer, LocalizedTextResolver(), settings()
                ),
            }
        )

        deliver(routing, OtpDeliveryChannel.SMS)
        deliver(routing, OtpDeliveryChannel.EMAIL)

        assert routing.available_channels() == {
            OtpDeliveryChannel.SMS,
            OtpDeliveryChannel.EMAIL,
        }
        assert len(sms.sent) == len(mailer.sent) == 1
        with pytest.raises(ExternalServiceError, match="whatsapp are not available"):
            deliver(routing, OtpDeliveryChannel.WHATSAPP)


class TestProviderSelection:
    def build(
        self,
        app_settings: AppSettings,
        sms: FakeSms | None = None,
        mailer: FakeMailer | None = None,
    ) -> OtpDeliveryFacilitatorContract:
        return build_otp_delivery_facilitator(
            settings=app_settings,
            sms_client=sms,
            telegram_gateway_client=None,
            whatsapp_client=None,
            email_client=mailer,
            localized_text_resolver=LocalizedTextResolver(),
        )

    def test_development_logs_codes_of_channels_without_a_provider(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        sms = FakeSms()
        facilitator = self.build(settings(), sms=sms)

        with caplog.at_level(logging.WARNING):
            deliver(facilitator, OtpDeliveryChannel.SMS)
            deliver(facilitator, OtpDeliveryChannel.EMAIL)

        assert facilitator.available_channels() == ALL_CHANNELS
        assert len(sms.sent) == 1
        assert "Login code 042317" in caplog.text
        assert "via email" in caplog.text
        assert "via sms" not in caplog.text

    def test_production_offers_only_configured_providers(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        mailer = FakeMailer()
        facilitator = self.build(settings(APP_ENV="production"), mailer=mailer)

        with (
            caplog.at_level(logging.DEBUG),
            pytest.raises(ExternalServiceError, match="sms are not available"),
        ):
            deliver(facilitator, OtpDeliveryChannel.SMS)
        deliver(facilitator, OtpDeliveryChannel.EMAIL)

        assert facilitator.available_channels() == {OtpDeliveryChannel.EMAIL}
        assert len(mailer.sent) == 1
        assert "042317" not in caplog.text

    def test_production_without_providers_refuses_every_code(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        facilitator = self.build(settings(APP_ENV="production"))

        with caplog.at_level(logging.DEBUG):
            for channel in OtpDeliveryChannel:
                with pytest.raises(ExternalServiceError, match="no provider"):
                    deliver(facilitator, channel)

        assert facilitator.available_channels() == frozenset()
        assert "042317" not in caplog.text

    def test_test_environment_can_switch_code_logging_off(self) -> None:
        facilitator = self.build(settings(APP_ENV="test", OTP_LOG_CODES="false"))

        assert facilitator.available_channels() == frozenset()

    def test_clients_exist_only_with_complete_settings(self) -> None:
        empty = settings()
        configured = settings(
            **TWILIO_ENVIRONMENT,
            **SMTP_ENVIRONMENT,
            **WHATSAPP_ENVIRONMENT,
            TELEGRAM_GATEWAY_API_TOKEN="gateway-token",
        )

        assert build_twilio_messaging_client(empty) is None
        assert build_telegram_gateway_client(empty) is None
        assert build_whatsapp_authentication_client(empty) is None
        assert build_smtp_email_client(empty) is None
        assert build_twilio_messaging_client(configured) is not None
        assert build_telegram_gateway_client(configured) is not None
        assert build_whatsapp_authentication_client(configured) is not None
        assert build_smtp_email_client(configured) is not None


class TestLoginCodeSettings:
    def test_complete_providers_are_read(self) -> None:
        app_settings = settings(
            **TWILIO_ENVIRONMENT,
            **SMTP_ENVIRONMENT,
            **WHATSAPP_ENVIRONMENT,
            SMTP_SECURITY="ssl",
            SMTP_USERNAME="mailer",
            SMTP_PASSWORD="smtp-password",
            WHATSAPP_OTP_TEMPLATE_LANGUAGES="ru, en ,pt_BR",
            TELEGRAM_GATEWAY_API_TOKEN="gateway-token",
        )

        assert app_settings.twilio_sender == "Workshop"
        assert app_settings.smtp_security is SmtpSecurity.SSL
        assert app_settings.smtp_port == 465
        assert app_settings.whatsapp_otp_access_token == "system-user-token"
        assert app_settings.whatsapp_otp_template_languages == ["ru", "en", "pt_BR"]
        assert app_settings.telegram_gateway_api_token == "gateway-token"

    def test_defaults(self) -> None:
        app_settings = settings()

        assert app_settings.smtp_port == 587
        assert app_settings.smtp_security is SmtpSecurity.STARTTLS
        assert app_settings.whatsapp_otp_template_languages == ["en"]
        assert app_settings.twilio_account_sid is None

    @pytest.mark.parametrize(
        ("environment", "expected"),
        [
            ({"TWILIO_ACCOUNT_SID": "AC" + "1f" * 16}, "TWILIO_AUTH_TOKEN"),
            (
                {"TWILIO_ACCOUNT_SID": "AC" + "1f" * 16, "TWILIO_AUTH_TOKEN": "t"},
                "TWILIO_FROM_NUMBER or TWILIO_MESSAGING_SERVICE_SID",
            ),
            (
                {**TWILIO_ENVIRONMENT, "TWILIO_ACCOUNT_SID": "SK123"},
                "TWILIO_ACCOUNT_SID",
            ),
            (
                {**TWILIO_ENVIRONMENT, "TWILIO_FROM_NUMBER": "12345"},
                "TWILIO_FROM_NUMBER",
            ),
            ({"WHATSAPP_OTP_TEMPLATE": "login_code"}, "WHATSAPP_OTP_PHONE_NUMBER_ID"),
            (
                {**WHATSAPP_ENVIRONMENT, "WHATSAPP_OTP_TEMPLATE_LANGUAGES": "english"},
                "WHATSAPP_OTP_TEMPLATE_LANGUAGES",
            ),
            ({"SMTP_HOST": "smtp.workshop.example"}, "SMTP_FROM"),
            ({**SMTP_ENVIRONMENT, "SMTP_USERNAME": "mailer"}, "SMTP_PASSWORD"),
            ({**SMTP_ENVIRONMENT, "SMTP_FROM": "not an address"}, "SMTP_FROM"),
            ({**SMTP_ENVIRONMENT, "SMTP_PORT": "70000"}, "SMTP_PORT"),
            ({"APP_ENV": "production", "OTP_LOG_CODES": "true"}, "OTP_LOG_CODES"),
        ],
    )
    def test_incomplete_or_invalid_providers_stop_the_start(
        self, environment: dict[str, str], expected: str
    ) -> None:
        with pytest.raises(ValidationFailedError, match=expected):
            assemble_app_settings(environment)


class TestStartupReport:
    def report(
        self, app_settings: AppSettings, caplog: pytest.LogCaptureFixture
    ) -> list[logging.LogRecord]:
        container = AppContainer()
        replace_provider(container.config.app_settings, app_settings)
        with caplog.at_level(logging.INFO, logger="app.main"):
            report_login_code_channels(container)

        return [record for record in caplog.records if record.name == "app.main"]

    def test_production_without_providers_is_an_error(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        [record] = self.report(settings(APP_ENV="production"), caplog)

        assert record.levelno == logging.ERROR
        assert "nobody can sign in" in record.getMessage()
        assert "SMTP_*" in record.getMessage()

    def test_configured_channels_are_listed(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        [record] = self.report(
            settings(APP_ENV="production", **SMTP_ENVIRONMENT, **TWILIO_ENVIRONMENT),
            caplog,
        )

        assert record.levelno == logging.INFO
        assert record.getMessage() == "Login codes can be sent by: email, sms"
