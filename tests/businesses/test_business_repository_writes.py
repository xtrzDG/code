"""
Every business write reads the stored revision and writes in one step: no
two writes share a revision, and `update` changes the business as stored.
"""

from collections.abc import Callable

import pytest

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.business_repositories import BusinessRepository
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName, CityName
from app.schemas.typings.users.prefixed_id import UserId
from tests.storage.builders import COUNTRY_SAMPLES, build_business


class SettingsSavedDuringAWrite(InMemoryDocumentCollectionAdapter[BusinessDocument]):
    """
    Runs another request's conditional save (a settings PATCH) once, at the
    latest moment a write of the business lets it in: after a plain read,
    or just before an atomic read-and-write.
    """

    def __init__(self) -> None:
        super().__init__(BusinessDocument)
        self.repo: BusinessRepository | None = None
        self.settings_revisions: list[int] = []

    def get(self, document_key: str) -> BusinessDocument | None:
        stored = super().get(document_key)
        self._save_settings_once(document_key)
        return stored

    def modify(
        self,
        document_key: str,
        change: Callable[[BusinessDocument], BusinessDocument | None],
    ) -> BusinessDocument | None:
        self._save_settings_once(document_key)
        return super().modify(document_key, change)

    def _save_settings_once(self, document_key: str) -> None:
        if self.repo is None or self.settings_revisions:
            return

        repo, self.repo = self.repo, None
        settings = repo.get(BusinessId(document_key))
        assert settings is not None
        settings.city = CityName("Berlin")
        assert repo.save_if_unchanged(settings)
        self.settings_revisions.append(int(settings.revision))


def stored_business() -> tuple[BusinessRepository, BusinessDocument]:
    repo = BusinessRepository(InMemoryDocumentCollectionAdapter(BusinessDocument))
    business = build_business(COUNTRY_SAMPLES[0], UserId())
    repo.save(business)
    return repo, business


def test_a_settings_save_during_a_blind_save_never_shares_its_revision() -> None:
    collection = SettingsSavedDuringAWrite()
    repo = BusinessRepository(collection)
    business = build_business(COUNTRY_SAMPLES[0], UserId())
    repo.save(business)
    base_revision = int(business.revision)
    stale_copy = repo.get(business.id)
    assert stale_copy is not None
    stale_copy.name = BusinessName("Stale copy")
    collection.repo = repo

    repo.save(stale_copy)

    stored = repo.get(business.id)
    assert stored is not None
    assert collection.settings_revisions == [base_revision + 1]
    # The later write gets the next revision, never the settings' one, so the
    # cabinet holding revision base+1 sees its next save refused as stale.
    assert stored.revision == base_revision + 2
    assert stale_copy.revision == base_revision + 2


def test_update_changes_the_business_as_stored_now() -> None:
    repo, business = stored_business()
    stale_copy = repo.get(business.id)
    assert stale_copy is not None
    meanwhile = repo.get(business.id)
    assert meanwhile is not None
    meanwhile.city = CityName("Berlin")
    assert repo.save_if_unchanged(meanwhile)

    def rename(current: BusinessDocument) -> None:
        current.name = BusinessName("Renamed")

    updated = repo.update(stale_copy.id, rename)

    stored = repo.get(business.id)
    assert stored is not None
    assert (stored.name, stored.city) == ("Renamed", "Berlin")
    assert stored.revision == updated.revision == int(meanwhile.revision) + 1


def test_an_update_that_changes_nothing_or_refuses_stores_nothing() -> None:
    repo, business = stored_business()

    def keep(current: BusinessDocument) -> None:
        current.name = business.name

    def refuse(current: BusinessDocument) -> None:
        current.name = BusinessName("Half done")
        raise ConflictError("Refused.")

    assert repo.update(business.id, keep).revision == business.revision
    with pytest.raises(ConflictError):
        repo.update(business.id, refuse)
    with pytest.raises(NotFoundError):
        repo.update(BusinessId(), keep)

    stored = repo.get(business.id)
    assert stored is not None
    assert (stored.name, stored.revision) == (business.name, business.revision)
