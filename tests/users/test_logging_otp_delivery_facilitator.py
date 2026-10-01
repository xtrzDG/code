import logging

import pytest

from app.facilitators.users.logging_otp_delivery_facilitator import (
    LoggingOtpDeliveryFacilitator,
)
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.users.constrained_strings import EmailAddress, OtpCode
from app.utilities.config_helpers.app_settings_assembler import assemble_app_settings


def test_development_logs_the_code_with_a_masked_destination(
    caplog: pytest.LogCaptureFixture,
) -> None:
    facilitator = LoggingOtpDeliveryFacilitator(assemble_app_settings({}))

    with caplog.at_level(logging.WARNING):
        facilitator.deliver(
            delivery_channel=OtpDeliveryChannel.WHATSAPP,
            phone_number=E164PhoneNumber("+995555123456"),
            email=None,
            code=OtpCode("042317"),
            language_tag=LanguageTag("ka"),
        )
        facilitator.deliver(
            delivery_channel=OtpDeliveryChannel.EMAIL,
            phone_number=None,
            email=EmailAddress("owner@example.com"),
            code=OtpCode("998877"),
            language_tag=LanguageTag("he"),
        )

    messages = [record.getMessage() for record in caplog.records]
    assert any("042317" in message and "whatsapp" in message for message in messages)
    assert any("+**********56" in message for message in messages)
    assert all("+995555123456" not in message for message in messages)
    assert any(
        "998877" in message and "o***r@example.com" in message for message in messages
    )


def test_production_without_a_provider_refuses_and_logs_nothing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    facilitator = LoggingOtpDeliveryFacilitator(
        assemble_app_settings({"APP_ENV": "production"})
    )

    with (
        caplog.at_level(logging.DEBUG),
        pytest.raises(ExternalServiceError, match="provider"),
    ):
        facilitator.deliver(
            delivery_channel=OtpDeliveryChannel.SMS,
            phone_number=E164PhoneNumber("+12015550123"),
            email=None,
            code=OtpCode("123456"),
            language_tag=LanguageTag("en"),
        )

    assert all("123456" not in record.getMessage() for record in caplog.records)
