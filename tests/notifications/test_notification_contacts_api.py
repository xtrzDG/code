"""Settings → Notifications over HTTP: staff contacts, their checks and links."""

from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.dto.notifications.staff_links import StaffLinkClaims
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.handoffs.constrained_strings import ManagerTelegramUsername
from app.utilities.notifications.cabinet_links import link_expiry
from tests.e2e.harness import bearer
from tests.e2e.harness_settings import CABINET_ORIGIN
from tests.notifications.notification_api_world import (
    Restaurant,
    contacts_by_name,
    open_restaurant_with_contacts,
    start_notifications_workshop,
)


def check(restaurant: Restaurant, key: str) -> tuple[int, dict[str, object]]:
    response = restaurant.workshop.client.post(
        f"{restaurant.base}/notification-contacts/{key}/test",
        json={},
        headers=restaurant.headers,
    )
    return response.status_code, response.json()


def test_the_owner_sees_each_contact_and_checks_it() -> None:
    workshop = start_notifications_workshop(push=None)
    with workshop.client:
        restaurant = open_restaurant_with_contacts(workshop)
        contacts = contacts_by_name(restaurant)
        assert {name: item["provider_ready"] for name, item in contacts.items()} == {
            "Nino": True,
            "Anna": False,
            "Gio": False,
            "Levan": False,
        }
        assert all(item["delivery"] is None for item in contacts.values())
        assert contacts["Nino"]["preferences"] == {
            "events": ["handoff", "lead", "booking"],
            "quiet_hours": None,
        }

        # Telegram goes through the platform bot, with the settings link.
        status, telegram = check(restaurant, str(contacts["Nino"]["key"]))
        assert status == 200, telegram
        assert telegram["delivery"]["status"] == "delivered"  # type: ignore[index]
        assert telegram["is_simulated"] is False
        [sent] = workshop.telegram.bodies("/sendMessage")
        assert sent["chat_id"] in (70001, "70001")
        assert f"{CABINET_ORIGIN}/n/" in str(sent["text"])

        # E-mail without SMTP is only logged outside production.
        status, email = check(restaurant, str(contacts["Anna"]["key"]))
        assert (status, email["is_simulated"]) == (200, True)
        assert email["delivery"]["status"] == "delivered"  # type: ignore[index]

        # WhatsApp without the template cannot deliver: the reason is shown.
        status, whatsapp = check(restaurant, str(contacts["Levan"]["key"]))
        assert status == 200
        assert whatsapp["delivery"]["status"] == "dead"  # type: ignore[index]
        assert whatsapp["is_simulated"] is False
        assert "WHATSAPP_NOTIFICATION" in str(whatsapp["delivery"])

        after = contacts_by_name(restaurant)
        assert after["Nino"]["delivery"]["status"] == "delivered"
        assert after["Levan"]["delivery"]["status"] == "dead"
        assert after["Gio"]["delivery"] is None


def test_checks_are_limited_per_contact_and_unknown_contacts_are_not_found() -> None:
    workshop = start_notifications_workshop(push=None)
    with workshop.client:
        restaurant = open_restaurant_with_contacts(workshop)
        key = str(contacts_by_name(restaurant)["Gio"]["key"])

        statuses = [check(restaurant, key)[0] for _ in range(6)]

        assert statuses == [200] * 5 + [429]
        limited = workshop.client.post(
            f"{restaurant.base}/notification-contacts/{key}/test",
            json={},
            headers=restaurant.headers,
        )
        assert int(limited.headers["Retry-After"]) > 0
        assert check(restaurant, "0" * 24)[0] == 404
        assert check(restaurant, "not-a-key")[0] == 404


def test_a_linked_telegram_contact_shows_its_username() -> None:
    workshop = start_notifications_workshop(push=None)
    with workshop.client:
        restaurant = open_restaurant_with_contacts(workshop)
        business = workshop.container.repositories.business_repo().get(
            BusinessId(restaurant.business_id)
        )
        assert business is not None
        nino, *others = business.manager_contacts
        business.manager_contacts = [
            nino.model_copy(
                update={"telegram_username": ManagerTelegramUsername("nino_salobie")}
            ),
            *others,
        ]
        workshop.container.repositories.business_repo().save(business)

        assert contacts_by_name(restaurant)["Nino"]["telegram_username"] == (
            "nino_salobie"
        )


def link_token(restaurant: Restaurant, claims: StaffLinkClaims) -> str:
    signer = restaurant.workshop.container.facilitators.staff_link_signer()
    return str(signer.sign(claims))


def test_a_signed_link_leads_to_its_page_until_it_expires() -> None:
    workshop = start_notifications_workshop(push=None)
    with workshop.client:
        restaurant = open_restaurant_with_contacts(workshop)
        conversation = ConversationId()
        token = link_token(
            restaurant,
            StaffLinkClaims(
                business_id=BusinessId(restaurant.business_id),
                target=StaffLinkTarget.CONVERSATION,
                conversation_id=conversation,
                expires_at=link_expiry(workshop.clock.wall_clock.now_unix()),
            ),
        )
        path = f"{restaurant.base}/notification-links/{token}"

        opened = workshop.client.get(path, headers=restaurant.headers)
        assert opened.status_code == 200, opened.text
        assert opened.json()["target"] == "conversation"
        assert opened.json()["conversation_id"] == str(conversation)
        assert opened.json()["is_expired"] is False

        # Signing in is still required, and another business's link is foreign.
        assert workshop.client.get(path).status_code == 401
        other_token, _ = workshop.sign_in_with_email("giulia@trattoria.example")
        assert workshop.client.get(path, headers=bearer(other_token)).status_code == 404
        forged = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
        assert (
            workshop.client.get(
                f"{restaurant.base}/notification-links/{forged}",
                headers=restaurant.headers,
            ).status_code
            == 404
        )

        # Eight days on (the session in use meanwhile, so it stays open).
        workshop.clock.advance(4 * 24 * 60 * 60)
        assert workshop.client.get(path, headers=restaurant.headers).status_code == 200
        workshop.clock.advance(4 * 24 * 60 * 60)
        expired = workshop.client.get(path, headers=restaurant.headers)
        assert expired.status_code == 200
        assert expired.json()["is_expired"] is True
        assert expired.json()["conversation_id"] is None
