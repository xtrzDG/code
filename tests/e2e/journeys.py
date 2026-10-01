"""Shared steps of the end-to-end journeys (a published Georgian restaurant)."""

from dataclasses import dataclass
from typing import Any

from tests.e2e.harness import Workshop, bearer

type JsonObject = dict[str, Any]

GEORGIAN_OWNER_PHONE: str = "+995 555 12 34 56"
WIDGET_SESSION: str = "visitor_0123456789abcdef"
BUSINESS_BOT_TOKEN: str = "7770001:AAHbusiness_bot_token_for_e2e_tests_0123"
BOOKING_REQUEST_RU: str = (
    "Здравствуйте! Хочу забронировать столик на завтра в 19:00 на двоих. "
    "Меня зовут Нино, телефон +995 555 12 34 56"
)
WIZARD_STEPS: dict[str, JsonObject] = {
    "niche_and_languages": {
        "answers_language": "ru",
        "answers": [{"question_key": "cuisine", "answer": "Грузинская"}],
    },
    "contacts_and_hours": {
        "address": {
            "text": "Тбилиси, проспект Руставели 1",
            "maps_url": "https://maps.example/salobie",
        },
        "hours": [
            {"weekday": weekday, "opens_at": 600, "closes_at": 1380}
            for weekday in range(1, 8)
        ],
        "contacts": {
            "public_phone_number": "+995 322 12 34 56",
            "handoff_phone_number": "555 98 76 54",
        },
    },
    "offer": {
        "items": [
            {"kind": "menu_item", "title": "ხაჭაპური", "price_minor": 1800},
            {"kind": "menu_item", "title": "Хинкали", "price_minor": 150},
        ]
    },
    "booking_rules": {
        "booking_rules": {
            "max_party_size": 8,
            "min_notice_minutes": 60,
            "cancellation_policy": "Бесплатная отмена за 2 часа.",
        }
    },
    "faq_and_handoff": {
        "faq": [{"question": "Есть парковка?", "answer": "Да, бесплатная."}],
        "handoff_rules": ["Банкет больше 20 человек"],
        "tone": "Дружелюбно и коротко",
    },
    "channels": {"links": [{"kind": "menu", "url": "https://salobie.example/menu"}]},
}


@dataclass(frozen=True)
class OpenRestaurant:
    """A Georgian restaurant whose assistant is published."""

    owner_token: str
    owner_id: str
    business_id: str
    version_id: str

    @property
    def base(self) -> str:
        return f"/v1/businesses/{self.business_id}"

    @property
    def headers(self) -> dict[str, str]:
        return bearer(self.owner_token)


def sign_in_and_create_restaurant(workshop: Workshop) -> tuple[str, str, str]:
    token, session = workshop.sign_in_with_phone(GEORGIAN_OWNER_PHONE)
    created = workshop.client.post(
        "/v1/businesses",
        json={"name": "Salobie Bia", "niche_key": "restaurant"},
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text
    return token, str(session["user"]["id"]), str(created.json()["id"])


def open_restaurant(workshop: Workshop) -> OpenRestaurant:
    """Sign in, fill the profile, add a table, assemble, test and publish."""

    client = workshop.client
    token, owner_id, business_id = sign_in_and_create_restaurant(workshop)
    headers = bearer(token)
    base = f"/v1/businesses/{business_id}"
    for step, body in WIZARD_STEPS.items():
        saved = client.put(f"{base}/profile/steps/{step}", json=body, headers=headers)
        assert saved.status_code == 200, (step, saved.text)

    table = client.post(
        f"{base}/resources",
        json={"name": "Стол у окна", "capacity": 4, "unit_count": 3},
        headers=headers,
    )
    assert table.status_code == 201, table.text
    settings = client.patch(
        base,
        json={
            "manager_contacts": [
                {
                    "name": "Гиорги",
                    "channel": "telegram",
                    "address": "70001",
                    "language": "ru",
                }
            ]
        },
        headers=headers,
    )
    assert settings.status_code == 200, settings.text
    version = client.post(
        f"{base}/assistant-versions",
        json={"run_autotests": False},
        headers=headers,
    )
    assert version.status_code == 201, version.text
    version_id = str(version.json()["id"])
    run = client.post(
        f"{base}/assistant-versions/{version_id}/autotests",
        json={"languages": ["ka"], "kinds": ["price_question"]},
        headers=headers,
    )
    assert run.status_code == 200, run.text
    published = client.post(
        f"{base}/assistant-versions/{version_id}/publish",
        json={},
        headers=headers,
    )
    assert published.status_code == 200, published.text
    return OpenRestaurant(token, owner_id, business_id, version_id)
