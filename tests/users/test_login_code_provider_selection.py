"""Choosing login code providers from settings, and the startup report."""

import logging

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
from app.main import report_login_code_channels
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.constants.messaging import SmtpSecurity
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from tests.e2e.workshop_container import replace_provider
from tests.users.login_code_fakes import (
    ALL_CHANNELS,
    SMTP_ENVIRONMENT,
    TWILIO_ENVIRONMENT,
    WHATSAPP_ENVIRONMENT,
    FakeMailer,
    FakeSms,
    deliver,
    settings,
)


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
