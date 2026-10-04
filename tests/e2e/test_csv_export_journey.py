"""
End to end over HTTP: the owner downloads the bookings and the inbox's
conversations as CSV (streamed, UTF-8 with a byte order mark, named after
the table and the day); staff are refused; a stale sign-in must step up.
"""

import csv
import io

from tests.e2e.harness import Workshop, bearer
from tests.e2e.journeys import BOOKING_REQUEST_RU, open_restaurant
from tests.e2e.telegram_customer import TelegramCustomer

BOM: str = "﻿"
STAFF_PHONE: str = "+995 555 77 66 55"


def test_the_owner_downloads_bookings_and_conversations(workshop: Workshop) -> None:
    client = workshop.client
    restaurant = open_restaurant(workshop)
    TelegramCustomer(workshop, restaurant).writes(BOOKING_REQUEST_RU)

    bookings = client.get(
        f"{restaurant.base}/exports/bookings",
        params={"language": "ru"},
        headers=restaurant.headers,
    )

    assert bookings.status_code == 200, bookings.text
    assert bookings.headers["content-type"] == "text/csv; charset=utf-8"
    assert bookings.headers["content-disposition"] == (
        'attachment; filename="bookings-2026-10-05.csv"'
    )
    assert bookings.headers["cache-control"] == "no-store"
    text = bookings.content.decode("utf-8")
    assert text.startswith(BOM)
    rows = list(csv.reader(io.StringIO(text.removeprefix(BOM))))
    assert rows[0][:3] == ["ID брони", "Дата", "Время"]
    assert len(rows) == 2
    assert rows[1][2] == "19:00"
    assert rows[1][9] == "Нино"

    conversations = client.get(
        f"{restaurant.base}/exports/conversations",
        params={"view": "all", "channel": "telegram"},
        headers=restaurant.headers,
    )
    assert conversations.status_code == 200, conversations.text
    messages = list(
        csv.reader(io.StringIO(conversations.content.decode("utf-8").lstrip(BOM)))
    )
    assert messages[0][-1] == "Message"
    assert [row[7] for row in messages[1:]] == ["customer", "assistant"]
    assert messages[1][-1] == BOOKING_REQUEST_RU

    unknown = client.get(
        f"{restaurant.base}/exports/invoices", headers=restaurant.headers
    )
    assert unknown.status_code == 404


def test_staff_are_refused_and_a_stale_sign_in_steps_up(workshop: Workshop) -> None:
    client = workshop.client
    restaurant = open_restaurant(workshop)
    invited = client.post(
        f"{restaurant.base}/members",
        json={"phone_number": STAFF_PHONE, "role": "staff"},
        headers=restaurant.headers,
    )
    assert invited.status_code == 201, invited.text
    staff = bearer(workshop.sign_in_with_phone(STAFF_PHONE)[0])

    refused = client.get(f"{restaurant.base}/exports/bookings", headers=staff)
    assert refused.status_code == 403

    workshop.clock.advance(11 * 60)
    stale = client.get(f"{restaurant.base}/exports/leads", headers=restaurant.headers)
    assert stale.status_code == 401
    assert stale.json()["reasons"][0]["code"] == "step_up_required"
    log = client.get(
        f"{restaurant.base}/audit-log",
        params={"action": "export"},
        headers=restaurant.headers,
    ).json()["items"]
    assert log == []
