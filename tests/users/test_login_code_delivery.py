"""Delivering login codes through each channel facilitator and routing."""

import pytest

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
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.channels.constrained_strings import (
    WhatsAppTemplateLanguageCode,
)
from app.schemas.typings.users.constrained_integers import OtpLifetimeSeconds
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from tests.users.login_code_fakes import (
    CODE,
    EMAIL,
    PHONE,
    FakeGateway,
    FakeMailer,
    FakeSms,
    FakeWhatsApp,
    deliver,
    settings,
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
