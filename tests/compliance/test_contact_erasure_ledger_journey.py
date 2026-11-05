"""
End to end over the real container: an owner erases a guest, the batch
worker records the erasure in the ledger outside the database, a restore
from a backup taken before brings the guest back, and the daily job, run
by its own operator (no business named, fail-closed storage), erases them
again inside their business's scope.
"""

from collections.abc import Iterator

import pytest
from typed_time_provider import Microseconds

from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.jobs import JobTick
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.platform.constrained_strings import JobName
from tests.bookings.conftest import CABINET_BASE_URL
from tests.bookings.manage_journey import book_a_table
from tests.e2e.harness import Workshop, start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT


@pytest.fixture
def workshop() -> Iterator[Workshop]:
    workshop = start_workshop({**E2E_ENVIRONMENT, "CABINET_BASE_URL": CABINET_BASE_URL})
    with workshop.client:
        yield workshop


def stored_contact(
    workshop: Workshop, business_id: BusinessId, contact_id: ContactId
) -> ContactDocument | None:
    container = workshop.container
    with container.utilities.storage_scope().scoped_to_business(business_id):
        return container.repositories.contact_repo().get(business_id, contact_id)


def test_an_erased_guest_restored_from_a_backup_is_erased_again(
    workshop: Workshop,
) -> None:
    booked = book_a_table(workshop)
    restaurant = booked.restaurant
    business_id = BusinessId(restaurant.business_id)
    [customer] = workshop.client.get(
        f"{restaurant.base}/contacts", headers=restaurant.headers
    ).json()["items"]
    contact_id = ContactId(customer["id"])
    before = stored_contact(workshop, business_id, contact_id)
    assert before is not None and before.erased_at is None
    erased = workshop.client.delete(
        f"{restaurant.base}/contacts/{contact_id}", headers=restaurant.headers
    )
    assert erased.status_code == 204, erased.text

    workshop.run_queued_jobs()

    ledger = workshop.container.use_cases.compliance.contact_erasure_ledger()
    [record] = ledger.read_all()
    assert (record.business_id, record.contact_id) == (business_id, contact_id)

    # The restore: the backup from before the erasure holds the guest again.
    container = workshop.container
    with container.utilities.storage_scope().platform_wide():
        container.repositories.contact_repo().save_many([before])
    restored = stored_contact(workshop, business_id, contact_id)
    assert restored is not None and restored.name == before.name
    workshop.clock.advance(60)

    report = container.operators.compliance.reapply_contact_erasures_operator().operate(
        JobTick(
            job_name=JobName("reapply_contact_erasures"),
            scheduled_at=Microseconds(0),
        )
    )

    assert int(report.processed_count) == 1
    again = stored_contact(workshop, business_id, contact_id)
    assert again is not None and again.erased_at is not None
    assert again.name is None and again.phone_number is None
