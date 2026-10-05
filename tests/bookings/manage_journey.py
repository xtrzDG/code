"""
A guest books a table through the website chat of the end-to-end
restaurant and gets the written confirmation with its manage link.
"""

import re
from dataclasses import dataclass

from tests.bookings.conftest import CABINET_BASE_URL
from tests.e2e.harness import Workshop
from tests.e2e.journeys import (
    BOOKING_REQUEST_RU,
    WIDGET_SESSION,
    JsonObject,
    OpenRestaurant,
    open_restaurant,
)
from tests.e2e.widget_turns import ask_widget

MANAGE_LINK_PATTERN: re.Pattern[str] = re.compile(
    re.escape(CABINET_BASE_URL) + r"/r/([A-Za-z0-9_-]+)"
)
BOOKINGS_PATH: str = "/v1/public/bookings"


@dataclass(frozen=True)
class BookedTable:
    restaurant: OpenRestaurant
    token: str
    confirmation: str
    cursor: str

    @property
    def page(self) -> str:
        return f"{BOOKINGS_PATH}/{self.token}"


def widget_messages_after(
    workshop: Workshop, restaurant: OpenRestaurant, after: str
) -> JsonObject:
    polled = workshop.client.get(
        f"/v1/widget/{restaurant.business_id}/messages",
        params={"after": after},
        headers={"X-Widget-Session-Key": WIDGET_SESSION},
    )
    assert polled.status_code == 200, polled.text
    body: JsonObject = polled.json()
    return body


def system_texts(polled: JsonObject) -> list[str]:
    return [str(item["text"]) for item in polled["items"] if item["author"] == "system"]


def manage_token(text: str) -> str:
    found = MANAGE_LINK_PATTERN.search(text)
    assert found is not None, text
    return found.group(1)


def book_a_table(workshop: Workshop) -> BookedTable:
    """The restaurant opens, a visitor says hello, then books for tomorrow."""

    restaurant = open_restaurant(workshop)
    web_chat = workshop.client.put(
        f"{restaurant.base}/channels/web", json={}, headers=restaurant.headers
    )
    assert web_chat.status_code == 200, web_chat.text
    greeted = ask_widget(
        workshop, restaurant.business_id, WIDGET_SESSION, "Здравствуйте!"
    )
    workshop.clock.advance(60)  # the widget orders messages by their time
    booked = ask_widget(
        workshop, restaurant.business_id, WIDGET_SESSION, BOOKING_REQUEST_RU
    )
    assert str(booked["text"]).endswith("Ваш столик забронирован на 19:00.")

    polled = widget_messages_after(workshop, restaurant, str(greeted["message_id"]))
    [confirmation] = system_texts(polled)
    return BookedTable(
        restaurant=restaurant,
        token=manage_token(confirmation),
        confirmation=confirmation,
        cursor=str(polled["cursor"]),
    )
