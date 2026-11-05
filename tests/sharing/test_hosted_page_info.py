"""
The hosted chat page as a link in bio: next to the chat it shows the
business's hours (in its time zone), its address with a map link, and a
"Book" button when the business takes bookings (its own booking page when
it has one, else the chat).
"""

from tests.e2e.harness import Workshop
from tests.e2e.journeys import JsonObject, open_restaurant


def hosted_config(workshop: Workshop, business_id: str) -> JsonObject:
    response = workshop.client.get(f"/v1/public/chat/{business_id}")
    assert response.status_code == 200, response.text
    body: JsonObject = response.json()
    return body


def test_the_page_shows_hours_address_and_bookings(workshop: Workshop) -> None:
    restaurant = open_restaurant(workshop)

    config = hosted_config(workshop, restaurant.business_id)

    assert config["timezone"] == "Asia/Tbilisi"
    assert config["hours"] == [
        {"weekday": weekday, "opens_at": 600, "closes_at": 1380}
        for weekday in range(1, 8)
    ]
    assert config["address"] == "Тбилиси, проспект Руставели 1"
    assert config["maps_url"] == "https://maps.example/salobie"
    assert config["takes_bookings"] is True
    assert config["booking_url"] is None


def test_the_business_own_booking_page_is_the_book_button(workshop: Workshop) -> None:
    restaurant = open_restaurant(workshop)
    saved = workshop.client.put(
        f"{restaurant.base}/profile/steps/channels",
        json={
            "links": [
                {"kind": "booking_page", "url": "https://salobie.example/book"},
            ]
        },
        headers=restaurant.headers,
    )
    assert saved.status_code == 200, saved.text

    config = hosted_config(workshop, restaurant.business_id)

    assert config["booking_url"] == "https://salobie.example/book"


def test_an_address_without_a_map_link_gets_a_maps_search(workshop: Workshop) -> None:
    restaurant = open_restaurant(workshop)
    saved = workshop.client.put(
        f"{restaurant.base}/profile/steps/contacts_and_hours",
        json={
            "address": {"text": "Batumi, Gorgiladze 5"},
            "hours": [{"weekday": 1, "opens_at": 540, "closes_at": 1080}],
            "contacts": {"public_phone_number": "+995 322 12 34 56"},
        },
        headers=restaurant.headers,
    )
    assert saved.status_code == 200, saved.text

    config = hosted_config(workshop, restaurant.business_id)

    assert config["maps_url"] == (
        "https://www.google.com/maps/search/?api=1&query=Batumi%2C%20Gorgiladze%205"
    )
    assert config["hours"] == [{"weekday": 1, "opens_at": 540, "closes_at": 1080}]
