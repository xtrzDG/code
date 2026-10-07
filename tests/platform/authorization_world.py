"""
The world of the authorization matrix: the real application with the demo
data (business B, the busy restaurant: its owner, a staff member and a
record of every kind), and a second business A with its own owner and staff,
the strangers to B. The storage scope records each request's scopes.
"""

from collections.abc import Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, cast

from dependency_injector import providers
from typed_time_provider import Microseconds

from app.containers.app import AppContainer
from app.contracts.brain import MenuExtractionAdapterContract
from app.schemas.constants.knowledge import KnowledgeItemKind, KnowledgeItemSource
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.menu_import import MenuExtraction, MenuExtractionRequest
from app.schemas.dto.storage import StorageScope
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.menu_import.prefixed_id import MenuImportBatchId
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.e2e.workshop_container import OverridableProvider, replace_provider
from tests.operations.fake_google import FakeGoogle
from tests.platform.authorization_billing import billing_path_values
from tests.platform.authorization_calendars import calendar_path_values
from tests.platform.authorization_customers import customer_path_values
from tests.platform.authorization_inbox import inbox_path_values
from tests.platform.authorization_integrations import integration_path_values
from tests.platform.authorization_notifications import notification_path_values
from tests.platform.authorization_privacy import privacy_path_values
from tests.platform.authorization_teaching import teaching_path_values
from tests.platform.authorization_value import value_path_values

type JsonObject = dict[str, Any]
type Headers = dict[str, str]

DEMO_OWNER_EMAIL: str = "demo@example.com"
DEMO_STAFF_PHONE: str = "+995 555 00 00 02"
DEMO_RESTAURANT: str = "Mtsvane Ezo"
STRANGER_OWNER_PHONE: str = "+995 555 12 34 56"
STRANGER_STAFF_PHONE: str = "+995 555 65 43 21"
# Lists of business B whose first row names a path parameter.
LISTED_IDS: dict[str, str] = {
    "booking_id": "bookings",
    "contact_id": "contacts",
    "conversation_id": "conversations",
    "handoff_id": "handoffs",
    "item_id": "knowledge",
    "lead_id": "leads",
    "question_id": "unanswered-questions",
    "resource_id": "resources",
    "exception_id": "schedule-exceptions",
    "entry_id": "waitlist",
}


class EmptyMenuExtractor(MenuExtractionAdapterContract):
    """The menu model of this world: it finds no dishes (and calls no one)."""

    def extract(self, request: MenuExtractionRequest) -> MenuExtraction:
        del request
        return MenuExtraction(items=[])


class RecordingStorageScope(StorageScopeContext):
    """The process's storage scope, remembering every scope entered."""

    def __init__(self) -> None:
        super().__init__()
        self.entered: list[StorageScope] = []

    @contextmanager
    def scoped_to_business(self, business_id: BusinessId) -> Generator[StorageScope]:
        with super().scoped_to_business(business_id) as scope:
            self.entered.append(scope)
            yield scope

    @contextmanager
    def platform_wide(self) -> Generator[StorageScope]:
        with super().platform_wide() as scope:
            self.entered.append(scope)
            yield scope


@dataclass
class AuthorizationWorld:
    """Who calls, and the ids of business B's records by path parameter."""

    workshop: Workshop
    storage_scope: RecordingStorageScope
    business_a: str
    business_b: str
    owner_a: Headers
    staff_a: Headers
    owner_b: Headers
    staff_b: Headers
    path_values: dict[str, str] = field(default_factory=dict[str, str])


@contextmanager
def open_authorization_world(
    environment: Mapping[str, str] = E2E_ENVIRONMENT,
) -> Generator[AuthorizationWorld]:
    """Start the application with the demo data and sign everyone in."""

    storage_scope = RecordingStorageScope()

    def install_edges(container: AppContainer) -> None:
        replace_provider(container.utilities.storage_scope, storage_scope)
        # The contract, not the OpenAI-backed class: override directly.
        cast(OverridableProvider, container.adapters.menu_extraction_adapter).override(
            providers.Object(EmptyMenuExtractor())
        )
        replace_provider(
            container.clients.google_calendar_client, FakeGoogle().client()
        )

    workshop = start_workshop(
        {**environment, "SEED_DEMO_DATA": "true"},
        prepare=install_edges,
    )
    with workshop.client:
        yield build_world(workshop, storage_scope)


def build_world(
    workshop: Workshop,
    storage_scope: RecordingStorageScope,
) -> AuthorizationWorld:
    client = workshop.client
    owner_b = bearer(workshop.sign_in_with_email(DEMO_OWNER_EMAIL)[0])
    staff_b = bearer(workshop.sign_in_with_phone(DEMO_STAFF_PHONE)[0])
    business_b: JsonObject = next(
        business
        for business in client.get("/v1/businesses", headers=owner_b).json()
        if business["name"] == DEMO_RESTAURANT
    )
    owner_a = bearer(workshop.sign_in_with_phone(STRANGER_OWNER_PHONE)[0])
    created = client.post(
        "/v1/businesses",
        json={"name": "Salobie", "niche_key": "restaurant"},
        headers=owner_a,
    )
    assert created.status_code == 201, created.text
    business_a = str(created.json()["id"])
    invited = client.post(
        f"/v1/businesses/{business_a}/members",
        json={"phone_number": STRANGER_STAFF_PHONE, "role": "staff"},
        headers=owner_a,
    )
    assert invited.status_code == 201, invited.text
    staff_a = bearer(workshop.sign_in_with_phone(STRANGER_STAFF_PHONE)[0])
    world = AuthorizationWorld(
        workshop=workshop,
        storage_scope=storage_scope,
        business_a=business_a,
        business_b=str(business_b["id"]),
        owner_a=owner_a,
        staff_a=staff_a,
        owner_b=owner_b,
        staff_b=staff_b,
    )
    world.path_values = discover_path_values(world, business_b)
    return world


def discover_path_values(
    world: AuthorizationWorld,
    business_b: JsonObject,
) -> dict[str, str]:
    """
    A real record of business B for every path parameter: one its owner
    can read, so a stranger's 404 is the isolation, not a missing record.
    """

    client = world.workshop.client
    base = f"/v1/businesses/{world.business_b}"
    values: dict[str, str] = {
        "business_id": world.business_b,
        "channel": "telegram",
        "step": "faq_and_handoff",
        "setup_step": "offer",
        "kind": "went_live",
        "table": "bookings",
        "mark": "printed_qr",
        "user_id": next(
            str(member["user_id"])
            for member in business_b["members"]
            if member["role"] == "staff"
        ),
    }
    for parameter, list_path in LISTED_IDS.items():
        listed = client.get(f"{base}/{list_path}", headers=world.owner_b).json()
        rows = cast(
            list[JsonObject], listed if isinstance(listed, list) else listed["items"]
        )
        values[parameter] = str(rows[0]["id"])

    versions = client.get(f"{base}/assistant-versions", headers=world.owner_b).json()
    values["version_id"] = next(
        str(version["id"]) for version in versions if version["status"] == "published"
    )
    values["call_id"] = find_call(world)
    values["batch_id"] = seed_import_batch(world)
    values["media_id"] = find_media(world)
    values.update(
        notification_path_values(
            world.workshop, world.storage_scope, world.business_b, world.owner_b
        )
    )
    values.update(
        value_path_values(world.workshop, world.storage_scope, world.business_b)
    )
    values.update(
        billing_path_values(world.workshop, world.storage_scope, world.business_b)
    )
    values.update(
        privacy_path_values(world.workshop, world.storage_scope, world.business_b)
    )
    values.update(
        inbox_path_values(
            world.workshop,
            world.business_b,
            values["conversation_id"],
            world.owner_b,
            world.staff_b,
        )
    )
    values.update(
        teaching_path_values(
            world.workshop, world.business_b, values["conversation_id"], world.owner_b
        )
    )
    values.update(customer_path_values(world.workshop, world.business_b, world.owner_b))
    values.update(
        calendar_path_values(
            world.workshop, world.storage_scope, world.business_b, values["resource_id"]
        )
    )
    values.update(
        integration_path_values(world.workshop, world.business_b, world.owner_b)
    )
    return values


def find_call(world: AuthorizationWorld) -> str:
    """A phone call of business B (the demo keeps no recordings)."""

    client = world.workshop.client
    base = f"/v1/businesses/{world.business_b}"
    conversations = client.get(
        f"{base}/conversations?limit=100", headers=world.owner_b
    ).json()["items"]
    for conversation in conversations:
        detail: JsonObject = client.get(
            f"{base}/conversations/{conversation['id']}", headers=world.owner_b
        ).json()
        calls = cast(list[JsonObject], detail.get("calls") or [])
        if calls:
            return str(calls[0]["id"])

    raise AssertionError("The demo restaurant has no phone call.")


def find_media(world: AuthorizationWorld) -> str:
    """A voice note or photo a customer of business B sent (demo data)."""

    business_id = BusinessId(world.business_b)
    with world.storage_scope.scoped_to_business(business_id):
        files = world.workshop.container.repositories.message_media_repo()
        stored = files.list_created_before(business_id, Microseconds(2**62))

    assert stored, "The demo restaurant has no customer media."
    return str(stored[0].id)


def seed_import_batch(world: AuthorizationWorld) -> str:
    """A menu-import draft of business B (the demo has none)."""

    container = world.workshop.container
    business_id = BusinessId(world.business_b)
    batch_id = MenuImportBatchId()
    draft = KnowledgeItemDocument(
        business_id=business_id,
        kind=KnowledgeItemKind.MENU_ITEM,
        title=KnowledgeTitle("Imported tea"),
        is_active=False,
        source=KnowledgeItemSource.MENU_IMPORT,
        import_batch_id=batch_id,
    )
    with world.storage_scope.scoped_to_business(business_id):
        container.repositories.knowledge_item_repo().save(draft)

    return str(batch_id)
