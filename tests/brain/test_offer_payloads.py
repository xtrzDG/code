"""What the model reads back: services with ids, stay prices and booking values."""

import json
from typing import Any

from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.conversations.offer_payloads import major_units
from app.utilities.conversations.tool_payloads import (
    render_availability,
    render_booking,
    render_price_lookup,
)
from tests.bookings.hotel_fixture import GuestHouse
from tests.bookings.salon_fixture import Salon


def parsed(payload: str) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(payload)
    return result


def test_availability_without_a_service_lists_the_bookable_ones_with_ids() -> None:
    salon = Salon()

    payload = parsed(render_availability(salon.query(time="12:00")))

    services = {service["title"]: service for service in payload["bookable_services"]}
    assert set(services) == {"Haircut", "Manicure"}
    haircut = services["Haircut"]
    assert haircut["service_id"] == str(salon.haircut.id)
    assert (haircut["duration_minutes"], haircut["price"], haircut["currency"]) == (
        45,
        "45.00",
        "GEL",
    )
    assert {performer["name"] for performer in haircut["performed_by"]} == {
        "Nino",
        "Levan",
    }
    assert "service" not in payload


def test_availability_of_a_service_names_it_and_its_masters() -> None:
    salon = Salon()

    payload = parsed(
        render_availability(salon.query(service="Manicure", time="12:00"), "2026-10-05")
    )

    assert payload["service"]["title"] == "Manicure"
    assert payload["service"]["performed_by"] == [
        {"resource_id": str(salon.mariam.id), "name": "Mariam"}
    ]
    assert "bookable_services" not in payload
    assert payload["business_today"] == "2026-10-05"
    assert {slot["resource_name"] for slot in payload["slots"]} == {"Mariam"}


def test_a_booking_names_its_service_and_value() -> None:
    salon = Salon()

    payload = parsed(render_booking(salon.book(service="Haircut", resource="Nino")))

    assert payload["service"] == "Haircut"
    assert (payload["price"], payload["currency"]) == ("45.00", "GEL")
    assert (payload["time"], payload["end_time"]) == ("12:00", "12:45")


def test_a_stay_carries_its_nightly_rates_and_total() -> None:
    house = GuestHouse()

    payload = parsed(render_availability(house.query("2027-08-30", 3, "deluxe")))

    stay = payload["slots"][0]["stay_price"]
    assert (stay["check_in"], stay["check_out"], stay["nights"]) == (
        "2027-08-30",
        "2027-09-02",
        3,
    )
    assert (stay["total"], stay["currency"]) == ("800.00", "GEL")
    assert stay["nightly"] == [
        {"date": "2027-08-30", "rate": "300.00", "season": "Summer"},
        {"date": "2027-08-31", "rate": "300.00", "season": "Summer"},
        {"date": "2027-09-01", "rate": "200.00"},
    ]


def test_get_price_shows_the_seasons_and_the_asked_stay() -> None:
    house = GuestHouse()

    payload = parsed(render_price_lookup(house.price("deluxe", "2027-12-31", 2)))

    deluxe = payload["matches"][0]
    assert deluxe["seasonal_nightly_rates"] == [
        {"from": "07-01", "to": "08-31", "nightly_rate": "300.00", "season": "Summer"},
        {
            "from": "12-20",
            "to": "01-10",
            "nightly_rate": "350.00",
            "season": "Holidays",
        },
    ]
    quote = payload["stay_quotes"][0]
    assert (quote["title"], quote["total"]) == ("Deluxe room", "700.00")
    assert [night["date"] for night in quote["nightly"]] == [
        "2027-12-31",
        "2028-01-01",
    ]


def test_major_units_keep_the_currency_precision() -> None:
    assert major_units(51700, CurrencyCode("GEL")) == "517.00"
    assert major_units(1500, CurrencyCode("JPY")) == "1500"
    assert major_units(12345, CurrencyCode("KWD")) == "12.345"
