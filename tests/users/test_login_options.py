"""GET /v1/auth/login-options: the sign-in ways that work right now."""

from app.schemas.constants.localization import OtpDeliveryChannel
from tests.users.accounts_testbed import build_accounts_testbed

PATH: str = "/v1/auth/login-options"


def test_country_channels_meet_the_configured_providers() -> None:
    testbed = build_accounts_testbed()
    testbed.otp_delivery.channels = frozenset(
        {OtpDeliveryChannel.TELEGRAM, OtpDeliveryChannel.SMS}
    )
    client = testbed.build_http_client()

    georgia = client.get(PATH, params={"country_code": "GE"})
    israel = client.get(PATH, params={"country_code": "il"})

    assert georgia.status_code == 200
    assert georgia.json() == {
        "country_code": "GE",
        "phone_channels": ["sms", "telegram"],
        "configured_channels": ["sms", "telegram"],
        "is_phone_login_available": True,
        "is_email_login_available": False,
        "is_sign_up_restricted": False,
        # Before the first terms took effect (the testbed's clock).
        "terms_version": None,
        "privacy_version": None,
    }
    assert israel.json()["phone_channels"] == ["sms"]


def test_no_working_phone_channel_but_e_mail() -> None:
    testbed = build_accounts_testbed()
    testbed.otp_delivery.channels = frozenset(
        {OtpDeliveryChannel.TELEGRAM, OtpDeliveryChannel.EMAIL}
    )

    body = testbed.build_http_client().get(PATH, params={"country_code": "DE"}).json()

    assert body["phone_channels"] == []
    assert body["configured_channels"] == ["telegram", "email"]
    assert body["is_phone_login_available"] is False
    assert body["is_email_login_available"] is True


def test_without_a_country_every_configured_phone_channel_counts() -> None:
    testbed = build_accounts_testbed()
    testbed.otp_delivery.channels = frozenset(
        {OtpDeliveryChannel.WHATSAPP, OtpDeliveryChannel.SMS}
    )
    client = testbed.build_http_client()

    body = client.get(PATH).json()
    blank = client.get(PATH, params={"country_code": " "}).json()

    assert body == {
        "country_code": None,
        "phone_channels": ["sms", "whatsapp"],
        "configured_channels": ["sms", "whatsapp"],
        "is_phone_login_available": True,
        "is_email_login_available": False,
        "is_sign_up_restricted": False,
        # Before the first terms took effect (the testbed's clock).
        "terms_version": None,
        "privacy_version": None,
    }
    assert blank == body
    testbed.otp_delivery.channels = frozenset()
    nothing = client.get(PATH).json()
    assert nothing["is_phone_login_available"] is False
    assert nothing["is_email_login_available"] is False
    assert nothing["configured_channels"] == []


def test_restricted_and_unknown_countries() -> None:
    client = build_accounts_testbed().build_http_client()

    restricted = client.get(PATH, params={"country_code": "KP"}).json()
    unknown = client.get(PATH, params={"country_code": "ZZ"})
    malformed = client.get(PATH, params={"country_code": "Georgia"})

    assert restricted["is_sign_up_restricted"] is True
    assert restricted["is_phone_login_available"] is False
    assert restricted["phone_channels"] == []
    assert unknown.status_code == 422
    assert malformed.status_code == 422
    assert malformed.json()["error"] == "validation_failed"
