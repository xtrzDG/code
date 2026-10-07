"""
End to end over HTTP: the owner downloads the bookings and the inbox's
conversations as CSV (streamed, UTF-8 with a byte order mark, named after
the table and the day) and the full export by its signed link; staff are
refused; a stale sign-in must step up.
"""

import csv
import io
import json
import zipfile

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


def test_the_owner_downloads_the_full_export_by_a_one_time_link(
    workshop: Workshop,
) -> None:
    client = workshop.client
    restaurant = open_restaurant(workshop)
    TelegramCustomer(workshop, restaurant).writes(BOOKING_REQUEST_RU)

    asked = client.post(
        f"{restaurant.base}/business-exports",
        json={"language": "ka"},
        headers=restaurant.headers,
    )
    assert asked.status_code == 202, asked.text
    assert asked.json()["status"] == "queued"
    assert asked.json()["download_path"] is None

    workshop.run_queued_jobs()
    [ready] = client.get(
        f"{restaurant.base}/business-exports", headers=restaurant.headers
    ).json()["items"]
    assert ready["status"] == "ready"
    assert ready["downloads_left"] == 3
    made = client.post(
        f"{restaurant.base}/business-exports/{ready['id']}/download-link",
        headers=restaurant.headers,
    )
    assert made.status_code == 200, made.text
    link: str = made.json()["download_path"]

    # The link needs the session of the owner who asked; nothing cached.
    assert client.get(link).status_code == 401
    downloaded = client.get(link, headers=restaurant.headers)
    assert downloaded.status_code == 200, downloaded.text
    assert downloaded.headers["content-type"] == "application/zip"
    assert downloaded.headers["cache-control"] == "no-store"
    # Streamed a piece at a time: no length known before the last piece.
    assert "content-length" not in downloaded.headers
    with zipfile.ZipFile(io.BytesIO(downloaded.content)) as archive:
        names = set(archive.namelist())
        bookings_csv = archive.read("csv/bookings.csv").decode("utf-8")
        contacts = json.loads(archive.read("contacts.json"))
    assert {"business.json", "messages.json", "csv/conversations.csv"} <= names
    assert bookings_csv.startswith(BOM + "ჯავშნის ID,")
    assert [contact["name"] for contact in contacts] == ["Нино"]

    # Used once; a tampered or missing token is the same 404.
    assert client.get(link, headers=restaurant.headers).status_code == 404
    again = client.post(
        f"{restaurant.base}/business-exports/{ready['id']}/download-link",
        headers=restaurant.headers,
    ).json()["download_path"]
    tampered = again[:-2] + ("AA" if not again.endswith("AA") else "BB")
    assert client.get(tampered, headers=restaurant.headers).status_code == 404
    assert (
        client.get(again.split("?")[0], headers=restaurant.headers).status_code == 404
    )
    workshop.clock.advance(11 * 60)
    assert client.get(again, headers=restaurant.headers).status_code == 404
