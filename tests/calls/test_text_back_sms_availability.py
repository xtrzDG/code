"""
Settings → Calls says whether a business's text-backs can go by SMS, and
else why not: the carriers of the business's country accept its texts
only from a sender registered for it, which the platform does not offer
yet (`business_registration_required`, the US: none of its callers is
texted by SMS, whatever their number and whatever the platform has), the
platform has no SMS provider (`not_configured`), or its Twilio account
waits for a sender (`no_sender`). The owner's stored SMS switch never
changes.
"""

from typing import Any

import pytest

from app.schemas.constants.calls import TextBackChannel, TextBackStatus
from app.schemas.constants.messaging import SmsUnavailableReason
from app.use_cases.voice.call_settings.text_back_sms_availability import (
    TextBackSmsAvailability,
)
from tests.calls.call_fallback_steps import TWILIO_SETTINGS
from tests.calls.call_steps import (
    connect_whatsapp,
    missed_calls,
    report_missed_call,
    save_call_settings,
)
from tests.calls.calls_http import build_calls_http_client
from tests.calls.test_text_back_sms_destinations import (
    ITALIAN_MOBILE,
    TEMPLATE_MISSING,
    US_NUMBER,
)
from tests.channels.channels_payloads import bearer
from tests.channels.channels_settings import ITALY, UNITED_STATES, build_settings
from tests.channels.voice_setup import build_voice_setup
from tests.e2e import harness
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.e2e.journeys import GEORGIAN_OWNER_PHONE

TURN_SMS_ON: dict[str, bool] = {
    "is_text_back_enabled": True,
    "is_sms_fallback_enabled": True,
}


def sms_fields(body: dict[str, Any]) -> dict[str, Any]:
    """The view's SMS fields; available exactly when no reason stands against it."""

    assert body["is_sms_available"] is (body["sms_unavailable_reason"] is None)
    return {
        "is_sms_available": body["is_sms_available"],
        "sms_unavailable_reason": body["sms_unavailable_reason"],
        "is_sms_fallback_enabled": body["is_sms_fallback_enabled"],
    }


def read_and_turn_sms_on(
    environment: dict[str, str], country_code: str | None = None
) -> list[dict[str, Any]]:
    """
    The application's own wiring: the owner creates a restaurant (in their
    phone's country, Georgia, unless another is named), reads Settings →
    Calls and turns SMS on. The bodies of both answers.
    """

    workshop = harness.start_workshop({**E2E_ENVIRONMENT, **environment})
    with workshop.client:
        token, _ = workshop.sign_in_with_phone(GEORGIAN_OWNER_PHONE)
        fields = {"name": "Salobie Bia", "niche_key": "restaurant"}
        if country_code is not None:
            fields["country_code"] = country_code
        created = workshop.client.post(
            "/v1/businesses", json=fields, headers=harness.bearer(token)
        )
        assert created.status_code == 201, created.text
        path = f"/v1/businesses/{created.json()['id']}/call-settings"
        read = workshop.client.get(path, headers=harness.bearer(token)).json()
        saved = workshop.client.put(
            path, json=TURN_SMS_ON, headers=harness.bearer(token)
        ).json()
    return [read, saved]


@pytest.mark.parametrize(
    ("environment", "reason"),
    [({}, "not_configured"), (TWILIO_SETTINGS, "no_sender")],
)
def test_the_platform_says_why_it_sends_no_sms(
    environment: dict[str, str], reason: str
) -> None:
    # The Twilio account alone gives no SMS client, and the owner still
    # sets (and keeps) the SMS switch.
    for body in read_and_turn_sms_on(environment):
        assert sms_fields(body) == {
            "is_sms_available": False,
            "sms_unavailable_reason": reason,
            "is_sms_fallback_enabled": True,
        }


@pytest.mark.parametrize("environment", [{}, TWILIO_SETTINGS])
def test_a_us_business_hears_its_own_reason_first(
    environment: dict[str, str],
) -> None:
    # No sender of the platform ever lets a US business text by SMS: the
    # platform's passing reason ("until then, WhatsApp only") would promise
    # SMS that never comes.
    for body in read_and_turn_sms_on(environment, country_code="US"):
        assert sms_fields(body) == {
            "is_sms_available": False,
            "sms_unavailable_reason": "business_registration_required",
            "is_sms_fallback_enabled": True,
        }


def test_without_an_sms_client_sms_is_never_available() -> None:
    # Settings that name a sender, but no client to send with.
    setup = build_voice_setup(
        settings=build_settings(**TWILIO_SETTINGS, TWILIO_FROM_NUMBER="Workshop")
    )
    availability = TextBackSmsAvailability(
        None, setup.testbed.settings, setup.testbed.country_registry
    )

    assert availability.reason_for(setup.business) is (
        SmsUnavailableReason.NOT_CONFIGURED
    )


def test_a_us_business_needs_a_sender_registered_for_it() -> None:
    setup = build_voice_setup(country=UNITED_STATES)
    # The testbed has an SMS client: only the US carriers' rule refuses.
    client = build_calls_http_client(setup.testbed)
    path = f"/v1/businesses/{setup.business.id}/call-settings"

    read = client.get(path, headers=bearer("owner")).json()
    saved = client.put(path, json=TURN_SMS_ON, headers=bearer("owner")).json()

    for body in (read, saved):
        assert sms_fields(body) == {
            "is_sms_available": False,
            "sms_unavailable_reason": "business_registration_required",
            "is_sms_fallback_enabled": True,
        }
    stored = setup.testbed.call_settings_repo.get_by_business(setup.business.id)
    assert stored is not None
    assert stored.is_sms_fallback_enabled is True


@pytest.mark.parametrize("caller", [US_NUMBER, ITALIAN_MOBILE])
def test_the_text_backs_of_a_us_business_agree_with_the_view(caller: str) -> None:
    # No caller is texted by SMS, whatever the country of their number: not
    # even when WhatsApp refuses the template and the stored switch is on.
    setup = build_voice_setup(country=UNITED_STATES)
    save_call_settings(setup)
    connect_whatsapp(setup)
    setup.testbed.meta_transport.respond(
        "POST", r"/messages$", TEMPLATE_MISSING, status_code=404
    )

    report_missed_call(setup, caller=caller)
    setup.testbed.run_worker()

    [missed] = missed_calls(setup)
    assert missed.status is TextBackStatus.FAILED
    assert missed.channel is TextBackChannel.WHATSAPP
    assert setup.testbed.sms_client.sent == []


def test_an_italian_business_texts_its_callers_by_sms() -> None:
    setup = build_voice_setup(country=ITALY, conversation_language="it")
    client = build_calls_http_client(setup.testbed)

    body = client.get(
        f"/v1/businesses/{setup.business.id}/call-settings", headers=bearer("owner")
    ).json()

    assert sms_fields(body) == {
        "is_sms_available": True,
        "sms_unavailable_reason": None,
        "is_sms_fallback_enabled": True,
    }
