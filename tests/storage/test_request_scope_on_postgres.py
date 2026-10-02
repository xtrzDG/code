"""
Row-level security as the second line of defence, through the real
application on Postgres: a request for one business runs in its storage
scope, so even a repository that forgot its business filter cannot read
another business's rows.
"""

from typing import cast

from dependency_injector import providers

from app.containers.app import AppContainer
from app.repositories.knowledge_repositories import KnowledgeItemRepository
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.platform.strings import DatabaseUrl
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.e2e.workshop_container import OverridableProvider

FIRST_OWNER_PHONE: str = "+995 555 12 34 56"
SECOND_OWNER_PHONE: str = "+995 555 65 43 21"
BOT_TOKEN: str = "123456789:AAFirstBusinessBotTokenForTheTest0123"


class ForgetfulKnowledgeItemRepository(KnowledgeItemRepository):
    """A repository bug: it reads an item by id without its business filter."""

    def get(
        self,
        business_id: BusinessId,
        item_id: KnowledgeItemId,
    ) -> KnowledgeItemDocument | None:
        del business_id
        return self._collection.get(str(item_id))


def install_forgetful_repository(container: AppContainer) -> None:
    cast(OverridableProvider, container.repositories.knowledge_item_repo).override(
        providers.Singleton(
            ForgetfulKnowledgeItemRepository,
            collection=container.adapters.collections.knowledge_item_collection,
        )
    )


def open_business(workshop: Workshop, phone: str, name: str) -> tuple[str, str]:
    token, _ = workshop.sign_in_with_phone(phone)
    created = workshop.client.post(
        "/v1/businesses",
        json={"name": name, "niche_key": "restaurant"},
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text
    return token, str(created.json()["id"])


def test_a_business_request_cannot_read_another_business_rows(
    database_url: DatabaseUrl,
) -> None:
    workshop = start_workshop(
        {**E2E_ENVIRONMENT, "DATABASE_URL": str(database_url)},
        prepare=install_forgetful_repository,
    )
    with workshop.client as client:
        first_token, first_id = open_business(workshop, FIRST_OWNER_PHONE, "Salobie")
        second_token, second_id = open_business(
            workshop, SECOND_OWNER_PHONE, "Shavi Lomi"
        )
        secret = client.post(
            f"/v1/businesses/{second_id}/knowledge",
            json={"kind": "menu_item", "title": "Secret recipe", "price_minor": 999},
            headers=bearer(second_token),
        )
        assert secret.status_code == 201, secret.text
        secret_id = str(secret.json()["id"])

        own_read = client.get(
            f"/v1/businesses/{second_id}/knowledge/{secret_id}",
            headers=bearer(second_token),
        )
        cross_read = client.get(
            f"/v1/businesses/{first_id}/knowledge/{secret_id}",
            headers=bearer(first_token),
        )
        # Platform-wide (no business scope) the bug does leak the item.
        leaked = workshop.container.repositories.knowledge_item_repo().get(
            BusinessId(first_id), KnowledgeItemId(secret_id)
        )

    assert own_read.status_code == 200, own_read.text
    assert leaked is not None
    # Within the request's business scope row-level security hides the row.
    assert cross_read.status_code == 404, cross_read.text


def test_an_account_used_by_another_business_is_still_found(
    database_url: DatabaseUrl,
) -> None:
    workshop = start_workshop({**E2E_ENVIRONMENT, "DATABASE_URL": str(database_url)})
    with workshop.client as client:
        first_token, first_id = open_business(workshop, FIRST_OWNER_PHONE, "Salobie")
        second_token, second_id = open_business(
            workshop, SECOND_OWNER_PHONE, "Shavi Lomi"
        )
        first = client.put(
            f"/v1/businesses/{first_id}/channels/telegram",
            json={"bot_token": BOT_TOKEN},
            headers=bearer(first_token),
        )
        second = client.put(
            f"/v1/businesses/{second_id}/channels/telegram",
            json={"bot_token": BOT_TOKEN},
            headers=bearer(second_token),
        )

    assert first.status_code == 200, first.text
    # The check looks across businesses (explicitly platform-wide), so the
    # business scope of the request does not hide the first business's bot.
    assert second.status_code == 409, second.text
    assert "another business" in second.json()["message"]
