"""
A started workshop with the demo data, for the closure and deletion
journeys: the demo owner's restaurant (B) is closed and deleted, a
stranger's business (A) must stay exactly as it was.
"""

from collections.abc import Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_collection_registry import (
    InMemoryCollectionRegistry,
)
from app.containers.account_deletion.account_deletion_operator_factories import (
    AccountDeletionOperatorFactories,
)
from app.schemas.dto.jobs import JobTick
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import JobName
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT

type Headers = dict[str, str]
type JsonObject = dict[str, Any]

DEMO_OWNER_EMAIL: str = "demo@example.com"
DEMO_STAFF_PHONE: str = "+995 555 00 00 02"
DEMO_RESTAURANT: str = "Mtsvane Ezo"
STRANGER_OWNER_PHONE: str = "+995 555 12 34 56"
DAY_SECONDS: int = 24 * 60 * 60


@dataclass(frozen=True)
class ClosureWorld:
    workshop: Workshop
    business_b: str
    business_a: str
    owner_b: Headers
    staff_b: Headers
    owner_a: Headers

    @property
    def closure_path(self) -> str:
        return f"/v1/businesses/{self.business_b}/closure"

    def operators(self) -> AccountDeletionOperatorFactories:
        return self.workshop.container.use_cases.account_deletion_root().operators

    def close_b(self) -> JsonObject:
        closed = self.workshop.client.post(
            self.closure_path,
            json={"confirmation_name": DEMO_RESTAURANT},
            headers=self.owner_b,
        )
        assert closed.status_code == 200, closed.text
        result: JsonObject = closed.json()
        return result

    def tick(self, job: str) -> None:
        operators = self.operators()
        operator = {
            "queue_business_deletions": operators.queue_due_deletions,
            "offboard_unpaid_businesses": operators.offboard_unpaid_businesses,
            "reapply_deletion_ledger": operators.reapply_deletion_ledger,
        }[job]()
        operator.operate(
            JobTick(
                job_name=JobName(job),
                scheduled_at=self.workshop.clock.wall_clock.now_unix(),
            )
        )

    def rows_of(self, business_id: str) -> dict[str, int]:
        """The business's documents in every in-memory collection, by name."""

        registry: InMemoryCollectionRegistry = (
            self.workshop.container.clients.in_memory_collections()
        )
        counts: dict[str, int] = {}
        with self.workshop.container.utilities.storage_scope().platform_wide():
            for name, table in registry.tables():
                count = int(table.count_business_documents(BusinessId(business_id)))
                if count:
                    counts[str(name)] = counts.get(str(name), 0) + count

        return counts

    def now(self) -> Microseconds:
        return self.workshop.clock.wall_clock.now_unix()

    def sign_in_owner_b(self) -> Headers:
        """The owner again (a session idle for days ends; a deletion takes 30)."""

        return bearer(self.workshop.sign_in_with_email(DEMO_OWNER_EMAIL)[0])

    def delete_b_after_thirty_days(self) -> None:
        self.close_b()
        self.workshop.clock.advance(31 * DAY_SECONDS)
        self.tick("queue_business_deletions")
        self.workshop.run_queued_jobs()


@contextmanager
def open_closure_world(
    environment: Mapping[str, str] = E2E_ENVIRONMENT,
) -> Generator[ClosureWorld]:
    workshop = start_workshop({**environment, "SEED_DEMO_DATA": "true"})
    with workshop.client:
        client = workshop.client
        owner_b = bearer(workshop.sign_in_with_email(DEMO_OWNER_EMAIL)[0])
        staff_b = bearer(workshop.sign_in_with_phone(DEMO_STAFF_PHONE)[0])
        business_b = next(
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
        yield ClosureWorld(
            workshop=workshop,
            business_b=str(business_b["id"]),
            business_a=str(created.json()["id"]),
            owner_b=owner_b,
            staff_b=staff_b,
            owner_a=owner_a,
        )
