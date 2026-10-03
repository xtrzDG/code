"""The real application with the demo data, signed in as the demo owner and staff."""

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from app.schemas.domain.outbound_messages import OutboundMessageDocument
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import CABINET_ORIGIN, E2E_ENVIRONMENT

DEMO_OWNER_EMAIL: str = "demo@example.com"
DEMO_STAFF_PHONE: str = "+995 555 00 00 02"
DEMO_RESTAURANT: str = "Mtsvane Ezo"
REPORT_KEY_PREFIX: str = "staff:value_report:"


@dataclass
class ValueDemo:
    workshop: Workshop
    owner: dict[str, str]
    staff: dict[str, str]
    business_id: str

    @property
    def base(self) -> str:
        return f"/v1/businesses/{self.business_id}"

    def get(self, path: str, headers: dict[str, str] | None = None) -> Any:
        return self.workshop.client.get(
            f"{self.base}{path}", headers=headers or self.owner
        )

    def put(
        self, path: str, body: dict[str, Any], headers: dict[str, str] | None = None
    ) -> Any:
        return self.workshop.client.put(
            f"{self.base}{path}", json=body, headers=headers or self.owner
        )

    def report_messages(self) -> list[OutboundMessageDocument]:
        """Every value report the outbox holds, of every demo business."""

        container = self.workshop.container
        with container.utilities.storage_scope().platform_wide():
            stored = container.adapters.collections.outbound_message_collection()
            return [
                message
                for message in stored.list_all()
                if str(message.idempotency_key).startswith(REPORT_KEY_PREFIX)
            ]


@contextmanager
def open_value_demo() -> Generator[ValueDemo]:
    """Monday 2026-10-05 12:00 in Tbilisi, a month of demo activity behind."""

    workshop = start_workshop(
        {
            **E2E_ENVIRONMENT,
            "SEED_DEMO_DATA": "true",
            # Digests carry a link back to the report only with a cabinet address.
            "CABINET_BASE_URL": CABINET_ORIGIN,
        }
    )
    with workshop.client:
        owner = bearer(workshop.sign_in_with_email(DEMO_OWNER_EMAIL)[0])
        staff = bearer(workshop.sign_in_with_phone(DEMO_STAFF_PHONE)[0])
        business = next(
            business
            for business in workshop.client.get("/v1/businesses", headers=owner).json()
            if business["name"] == DEMO_RESTAURANT
        )
        yield ValueDemo(
            workshop=workshop, owner=owner, staff=staff, business_id=business["id"]
        )
