"""The current website import of a business, on in-memory and Postgres storage."""

import pytest
from typed_time_provider import Microseconds

from app.repositories.website_import_repository import WebsiteImportRepository
from app.schemas.constants.website_import import WebsiteImportStatus
from app.schemas.domain.website_imports import WebsiteImportDocument
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.menu_import.prefixed_id import MenuImportBatchId
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.website_import.constrained_integers import WebsitePageCount
from app.schemas.typings.website_import.prefixed_id import WebsiteImportId
from app.utilities.knowledge.website.website_import_keys import (
    derive_website_import_record_id,
)
from tests.storage.conftest import CollectionFactory
from tests.storage.storage_testing import FIXED_NANOSECONDS

pytestmark = pytest.mark.usefixtures("platform_scope")

NOW: Microseconds = Microseconds(FIXED_NANOSECONDS // 1_000)
MINUTE: int = 60_000_000


def new_import(
    business_id: BusinessId, updated_at: Microseconds = NOW
) -> WebsiteImportDocument:
    return WebsiteImportDocument(
        id=derive_website_import_record_id(business_id),
        business_id=business_id,
        import_id=WebsiteImportId(),
        batch_id=MenuImportBatchId(),
        url=WebLink("https://cafe.example"),
        status=WebsiteImportStatus.QUEUED,
        requested_by=UserId(),
        started_at=updated_at,
        created_at=updated_at,
        updated_at=updated_at,
    )


def test_one_import_runs_at_a_time_and_a_finished_one_is_replaced(
    collections: CollectionFactory,
) -> None:
    repo = WebsiteImportRepository(
        collections(WebsiteImportDocument, "website_imports")
    )
    business_id, other_business_id = BusinessId(), BusinessId()
    first = new_import(business_id)

    assert repo.start(first, Microseconds(int(NOW) - 15 * MINUTE)) is None
    blocking = repo.start(new_import(business_id), Microseconds(int(NOW) - MINUTE))
    assert blocking is not None and blocking.import_id == first.import_id
    assert repo.get_by_business(other_business_id) is None

    def finish(stored: WebsiteImportDocument) -> bool:
        stored.status = WebsiteImportStatus.DONE
        stored.pages_read = WebsitePageCount(3)
        return True

    done = repo.change(business_id, first.import_id, finish)
    assert done is not None and int(done.pages_read) == 3

    second = new_import(business_id)
    assert repo.start(second, NOW) is None
    current = repo.get_by_business(business_id)
    assert current is not None and current.import_id == second.import_id
    # The finished import's job can no longer touch the business's import.
    assert repo.change(business_id, first.import_id, finish) is None
    assert repo.change(other_business_id, second.import_id, finish) is None


def test_an_abandoned_import_is_replaced(collections: CollectionFactory) -> None:
    repo = WebsiteImportRepository(
        collections(WebsiteImportDocument, "website_imports")
    )
    business_id = BusinessId()
    repo.start(new_import(business_id, Microseconds(int(NOW) - 20 * MINUTE)), NOW)

    restarted = new_import(business_id)
    assert repo.start(restarted, Microseconds(int(NOW) - 15 * MINUTE)) is None

    current = repo.get_by_business(business_id)
    assert current is not None and current.import_id == restarted.import_id
    assert repo.change(business_id, restarted.import_id, lambda stored: False) is None
