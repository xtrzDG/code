"""
Twilio's phone numbers as the number picker uses them: the documented
AvailablePhoneNumbers page and price list read into offers and a monthly
price, the purchase form, and the documented errors the purchase tells
apart (a number taken since the search, a refused account, a 404 country).
"""

import base64
from typing import Any
from urllib.parse import parse_qsl

import httpx
import pytest

from app.clients.twilio.twilio_phone_numbers_client import TwilioPhoneNumbersClient
from app.schemas.constants.phone_numbers import PhoneNumberType
from app.schemas.dto.phone_numbers.provisioning import (
    PhoneNumberPurchase,
    PhoneNumberSearchQuery,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.phone_number_errors import PhoneNumberUnavailableError
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
)
from app.schemas.typings.messaging.constrained_strings import TwilioAccountSid
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.telephony.constrained_integers import PhoneNumberOfferCount
from app.schemas.typings.telephony.constrained_strings import (
    PhoneNumberCityQuery,
    PhoneNumberLabel,
)
from app.schemas.typings.telephony.strings import ProviderPhoneNumberId
from tests.channels.recording_transport import RecordingTransport
from tests.contracts.contract_files import load_json_fixture

ACCOUNT = TwilioAccountSid("AC" + "0" * 32)
TOKEN = PlatformSecret("test-token-0000")
AVAILABLE_PATH: str = r"/AvailablePhoneNumbers/US/Local\.json$"
PRICES_PATH: str = r"/v1/PhoneNumbers/Countries/US$"
BUY_PATH: str = r"/IncomingPhoneNumbers\.json$"
RELEASE_PATH: str = r"/IncomingPhoneNumbers/PN0+42\.json$"
PURCHASE = PhoneNumberPurchase(
    phone_number=E164PhoneNumber("+15125550142"),
    label=PhoneNumberLabel("Assistant Workshop: Austin Coffee Lab"),
)


def client(transport: RecordingTransport) -> TwilioPhoneNumbersClient:
    return TwilioPhoneNumbersClient(ACCOUNT, TOKEN, transport=transport.build())


def search_query(city: str | None = "Austin") -> PhoneNumberSearchQuery:
    return PhoneNumberSearchQuery(
        country_code=CountryCode("US"),
        number_type=PhoneNumberType.LOCAL,
        city=None if city is None else PhoneNumberCityQuery(city),
        limit=PhoneNumberOfferCount(10),
    )


def test_offers_are_voice_numbers_that_need_no_address() -> None:
    transport = RecordingTransport()
    transport.respond(
        "GET",
        AVAILABLE_PATH,
        load_json_fixture("twilio", "available_local_numbers.json"),
    )

    numbers = client(transport).list_available_numbers(search_query())

    assert [str(number.phone_number) for number in numbers] == [
        "+15125550142",
        "+15125550187",
    ]
    assert [str(number.locality) for number in numbers] == ["Austin", "Austin"]
    assert {str(number.region) for number in numbers} == {"TX"}
    [request] = transport.requests
    assert (
        request.url.path
        == f"/2010-04-01/Accounts/{ACCOUNT}/AvailablePhoneNumbers/US/Local.json"
    )
    assert dict(request.url.params) == {
        "VoiceEnabled": "true",
        "ExcludeAllAddressRequired": "true",
        "ExcludeLocalAddressRequired": "true",
        "ExcludeForeignAddressRequired": "true",
        "Beta": "false",
        "PageSize": "10",
        "InLocality": "Austin",
    }
    expected = base64.b64encode(f"{ACCOUNT}:{TOKEN}".encode()).decode()
    assert request.headers["authorization"] == f"Basic {expected}"


def test_a_search_without_a_city_asks_the_whole_country() -> None:
    transport = RecordingTransport()
    transport.respond(
        "GET",
        AVAILABLE_PATH,
        load_json_fixture("twilio", "available_local_numbers.json"),
    )

    client(transport).list_available_numbers(search_query(city=None))

    assert "InLocality" not in dict(transport.requests[0].url.params)


@pytest.mark.parametrize(
    ("number_type", "expected"),
    [
        (PhoneNumberType.LOCAL, CostMicroUsd(1_150_000)),
        (PhoneNumberType.TOLL_FREE, CostMicroUsd(2_150_000)),
        (PhoneNumberType.MOBILE, None),
    ],
)
def test_the_price_list_gives_the_monthly_price_of_each_kind(
    number_type: PhoneNumberType, expected: CostMicroUsd | None
) -> None:
    transport = RecordingTransport()
    transport.respond(
        "GET", PRICES_PATH, load_json_fixture("twilio", "phone_number_prices_us.json")
    )

    price = client(transport).get_monthly_price(CountryCode("US"), number_type)

    assert price == expected
    assert transport.requests[0].url.host == "pricing.twilio.com"


def test_a_price_list_in_another_currency_prices_nothing() -> None:
    transport = RecordingTransport()
    prices: dict[str, Any] = load_json_fixture("twilio", "phone_number_prices_us.json")
    transport.respond("GET", PRICES_PATH, {**prices, "price_unit": "EUR"})

    assert (
        client(transport).get_monthly_price(CountryCode("US"), PhoneNumberType.LOCAL)
        is None
    )


def test_renting_posts_the_number_and_its_label() -> None:
    transport = RecordingTransport()
    transport.respond(
        "POST",
        BUY_PATH,
        load_json_fixture("twilio", "incoming_phone_number_created.json"),
        201,
    )

    sid = client(transport).buy_number(PURCHASE)

    assert sid == ProviderPhoneNumberId("PN00000000000000000000000000000042")
    [request] = transport.requests
    assert dict(parse_qsl(request.body.decode())) == {
        "PhoneNumber": "+15125550142",
        "FriendlyName": "Assistant Workshop: Austin Coffee Lab",
    }


def test_returning_a_number_deletes_it() -> None:
    transport = RecordingTransport()
    transport.respond("DELETE", RELEASE_PATH, None, 204)

    client(transport).release_number(ProviderPhoneNumberId("PN" + "0" * 30 + "42"))

    assert [request.method for request in transport.requests] == ["DELETE"]


@pytest.mark.parametrize(
    "case",
    load_json_fixture("twilio", "phone_number_errors.json")["cases"],
    ids=lambda case: f"{case['operation']}-{case['status']}-{case['body']['code']}",
)
def test_documented_errors_become_the_errors_the_picker_shows(
    case: dict[str, Any],
) -> None:
    transport = RecordingTransport()
    paths: dict[str, tuple[str, str]] = {
        "buy": ("POST", BUY_PATH),
        "search": ("GET", r"/AvailablePhoneNumbers/"),
        "release": ("DELETE", RELEASE_PATH),
    }
    method, path = paths[case["operation"]]
    transport.respond(method, path, case["body"], case["status"])
    twilio = client(transport)

    def run() -> object:
        if case["operation"] == "buy":
            return twilio.buy_number(PURCHASE)
        if case["operation"] == "search":
            return twilio.list_available_numbers(search_query())
        twilio.release_number(ProviderPhoneNumberId("PN" + "0" * 30 + "42"))
        return None

    if case["expected"] == "unavailable":
        with pytest.raises(PhoneNumberUnavailableError):
            run()
    elif case["expected"] == "provider":
        with pytest.raises(ExternalServiceError) as raised:
            run()
        assert str(TOKEN) not in str(raised.value)
        assert "+1512" not in str(raised.value)
    else:
        assert run() in ([], None)


def test_a_network_failure_is_a_provider_error() -> None:
    transport = RecordingTransport()
    transport.failure = httpx.ConnectTimeout("timed out")

    with pytest.raises(ExternalServiceError, match="ConnectTimeout"):
        client(transport).buy_number(PURCHASE)
