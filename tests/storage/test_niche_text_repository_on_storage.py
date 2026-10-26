"""
The niche template editor's documents on both storages: one draft per
niche, the newest version of each niche by its indexed probe, a niche's
history newest first, and a version stored once even when two admins
publish it at the same moment (threads released together by a barrier).
"""

import threading

import pytest
from typed_time_provider import Microseconds

from app.repositories.niche_text_repository import NicheTextRepository
from app.schemas.constants.niches import NicheKey, NicheTextReleaseKind
from app.schemas.domain.niche_texts import (
    NicheTextDraftDocument,
    NicheTextEntry,
    NicheTextReleaseDocument,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.niches.constrained_integers import NicheTextVersion
from app.schemas.typings.niches.constrained_strings import (
    NicheOverrideText,
    NicheTextFieldKey,
)
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.niches.niche_text_identity import release_id_for
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.conftest import CollectionFactory

pytestmark = pytest.mark.usefixtures("platform_scope")

ADMIN: UserId = UserId()
PARALLEL_PUBLISHES: int = 6


def label(text: str) -> NicheTextEntry:
    return NicheTextEntry(
        field_key=NicheTextFieldKey("questions.cuisine.label"),
        language=LanguageTag("ru"),
        text=NicheOverrideText(text),
    )


def release(
    niche: NicheKey, version: int, text: str = "Кухня?"
) -> NicheTextReleaseDocument:
    return NicheTextReleaseDocument(
        id=release_id_for(niche, NicheTextVersion(version)),
        niche_key=niche,
        version=NicheTextVersion(version),
        kind=NicheTextReleaseKind.PUBLISH,
        entries=[label(text)],
        published_by=ADMIN,
        created_at=Microseconds(version),
        updated_at=Microseconds(version),
    )


def repository(collections: CollectionFactory) -> NicheTextRepository:
    return NicheTextRepository(
        collections(NicheTextDraftDocument, "niche_text_drafts"),
        collections(NicheTextReleaseDocument, "niche_text_releases"),
    )


def test_drafts_are_kept_per_niche(collections: CollectionFactory) -> None:
    repo = repository(collections)
    draft = NicheTextDraftDocument(
        niche_key=NicheKey.HOTEL, entries=[label("Номер?")], updated_by=ADMIN
    )

    repo.save_draft(draft)

    assert repo.get_draft(NicheKey.HOTEL) == draft
    assert repo.get_draft(NicheKey.RESTAURANT) is None
    assert repo.list_drafts([NicheKey.HOTEL, NicheKey.RESTAURANT]) == [draft]
    assert repo.list_drafts([]) == []
    repo.delete_draft(NicheKey.HOTEL)
    assert repo.get_draft(NicheKey.HOTEL) is None


def test_the_newest_version_of_each_niche_and_a_niches_history(
    collections: CollectionFactory,
) -> None:
    repo = repository(collections)
    for stored in (
        release(NicheKey.RESTAURANT, 1, "Первая?"),
        release(NicheKey.HOTEL, 1),
        release(NicheKey.RESTAURANT, 2, "Вторая?"),
        release(NicheKey.RESTAURANT, 3, "Третья?"),
    ):
        assert repo.add_release(stored)

    latest = {
        item.niche_key: int(item.version)
        for item in repo.latest_releases(
            [NicheKey.RESTAURANT, NicheKey.HOTEL, NicheKey.CLINIC]
        )
    }
    history = repo.list_releases(NicheKey.RESTAURANT, DocumentQueryLimit(2))

    assert latest == {NicheKey.RESTAURANT: 3, NicheKey.HOTEL: 1}
    assert [int(item.version) for item in history] == [3, 2]
    assert repo.latest_releases([]) == []
    found = repo.get_release(NicheKey.RESTAURANT, NicheTextVersion(2))
    assert found is not None and str(found.entries[0].text) == "Вторая?"
    assert repo.get_release(NicheKey.RESTAURANT, NicheTextVersion(9)) is None


def test_a_version_is_stored_once_when_admins_publish_it_together(
    collections: CollectionFactory, storage_scope: StorageScopeContext
) -> None:
    repo = repository(collections)
    results: list[bool] = []
    lock = threading.Lock()
    start = threading.Barrier(PARALLEL_PUBLISHES)

    def publish(text: str) -> None:
        start.wait()
        with storage_scope.platform_wide():
            stored = repo.add_release(release(NicheKey.CLINIC, 1, text))
        with lock:
            results.append(stored)

    threads = [
        threading.Thread(target=publish, args=(f"Вариант {index}?",))
        for index in range(PARALLEL_PUBLISHES)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(results) == [False] * (PARALLEL_PUBLISHES - 1) + [True]
    assert len(repo.list_releases(NicheKey.CLINIC, DocumentQueryLimit(10))) == 1
