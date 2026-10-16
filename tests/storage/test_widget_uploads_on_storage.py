"""
Website visitors' uploads on storage (1191): claimed once among concurrent
messages (a row lock on Postgres), only by their own visitor, hidden from
another business's scope by row-level security, and read by age for the
daily purge; the same on in-memory and on Postgres.
"""

import threading

from typed_time_provider import Microseconds

from app.repositories.widget_upload_repository import WidgetUploadRepository
from app.schemas.constants.media import AttachmentKind
from app.schemas.domain.widget_uploads import WidgetUploadDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.prefixed_id import WidgetVisitorId
from app.schemas.typings.media.constrained_integers import MediaByteCount
from app.schemas.typings.media.constrained_strings import MessageMediaType
from app.schemas.typings.media.prefixed_id import WidgetUploadId
from app.utilities.media.media_paths import widget_upload_storage_path
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.conftest import CollectionFactory, PostgresCollectionFactory

BUSINESS: BusinessId = BusinessId()
OTHER_BUSINESS: BusinessId = BusinessId()
VISITOR: WidgetVisitorId = WidgetVisitorId()
OTHER_VISITOR: WidgetVisitorId = WidgetVisitorId()
PARALLEL_MESSAGES: int = 8
NOW: int = 1_790_000_000_000_000


def upload_repo(collections: CollectionFactory) -> WidgetUploadRepository:
    return WidgetUploadRepository(collections(WidgetUploadDocument, "widget_uploads"))


def stored_upload(
    repo: WidgetUploadRepository,
    created_at: int = NOW,
    business_id: BusinessId = BUSINESS,
) -> WidgetUploadDocument:
    upload_id = WidgetUploadId()
    media_type = MessageMediaType("audio/webm")
    upload = WidgetUploadDocument(
        id=upload_id,
        business_id=business_id,
        visitor_id=VISITOR,
        kind=AttachmentKind.AUDIO,
        media_type=media_type,
        storage_path=widget_upload_storage_path(business_id, upload_id, media_type),
        byte_count=MediaByteCount(2048),
        created_at=Microseconds(created_at),
        updated_at=Microseconds(created_at),
    )
    repo.save(upload)
    return upload


def test_of_concurrent_messages_naming_one_upload_exactly_one_claims_it(
    collections: CollectionFactory, storage_scope: StorageScopeContext
) -> None:
    repo = upload_repo(collections)
    with storage_scope.scoped_to_business(BUSINESS):
        upload = stored_upload(repo)
    start = threading.Barrier(PARALLEL_MESSAGES)
    claims: list[bool] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def claim(index: int) -> None:
        start.wait()
        try:
            with storage_scope.scoped_to_business(BUSINESS):
                claimed = repo.claim(
                    BUSINESS, upload.id, VISITOR, Microseconds(NOW + index)
                )
        except BaseException as error:  # noqa: BLE001 - reported below
            with lock:
                errors.append(error)
            return
        with lock:
            claims.append(claimed is not None)

    threads = [
        threading.Thread(target=claim, args=(index,))
        for index in range(PARALLEL_MESSAGES)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert sorted(claims) == [False] * (PARALLEL_MESSAGES - 1) + [True]
    with storage_scope.scoped_to_business(BUSINESS):
        [stored] = repo.get_many(BUSINESS, [upload.id])
    assert stored.attached_at is not None


def test_only_its_own_visitor_claims_an_upload_and_a_release_frees_it(
    collections: CollectionFactory, storage_scope: StorageScopeContext
) -> None:
    repo = upload_repo(collections)
    with storage_scope.scoped_to_business(BUSINESS):
        upload = stored_upload(repo)

        by_other = repo.claim(BUSINESS, upload.id, OTHER_VISITOR, Microseconds(NOW))
        by_owner = repo.claim(BUSINESS, upload.id, VISITOR, Microseconds(NOW))
        again = repo.claim(BUSINESS, upload.id, VISITOR, Microseconds(NOW + 1))
        repo.release(BUSINESS, upload.id)
        after_release = repo.claim(BUSINESS, upload.id, VISITOR, Microseconds(NOW + 2))

    assert by_other is None
    assert by_owner is not None and by_owner.attached_at == NOW
    assert again is None
    assert after_release is not None and after_release.attached_at == NOW + 2


def test_another_business_neither_reads_nor_claims_an_upload(
    collections: CollectionFactory, storage_scope: StorageScopeContext
) -> None:
    repo = upload_repo(collections)
    with storage_scope.scoped_to_business(BUSINESS):
        upload = stored_upload(repo)

    with storage_scope.scoped_to_business(OTHER_BUSINESS):
        named_by_other = repo.get_many(OTHER_BUSINESS, [upload.id])
        claimed_by_other = repo.claim(
            OTHER_BUSINESS, upload.id, VISITOR, Microseconds(NOW)
        )

    assert named_by_other == []
    assert claimed_by_other is None


def test_row_level_security_hides_an_upload_from_another_business_scope(
    postgres_collections: PostgresCollectionFactory,
    storage_scope: StorageScopeContext,
) -> None:
    repo = upload_repo(postgres_collections)
    with storage_scope.scoped_to_business(BUSINESS):
        upload = stored_upload(repo)

    # The right business named, but from another business's scope: no row.
    with storage_scope.scoped_to_business(OTHER_BUSINESS):
        read = repo.get_many(BUSINESS, [upload.id])
        claimed = repo.claim(BUSINESS, upload.id, VISITOR, Microseconds(NOW))
        stale = repo.list_created_before(BUSINESS, Microseconds(NOW + 1))

    assert (read, claimed, stale) == ([], None, [])
    with storage_scope.scoped_to_business(BUSINESS):
        [stored] = repo.get_many(BUSINESS, [upload.id])
    assert stored.attached_at is None


def test_the_purge_reads_only_uploads_older_than_its_cutoff(
    collections: CollectionFactory, storage_scope: StorageScopeContext
) -> None:
    repo = upload_repo(collections)
    with storage_scope.scoped_to_business(BUSINESS):
        oldest = stored_upload(repo, created_at=NOW - 3)
        older = stored_upload(repo, created_at=NOW - 2)
        stored_upload(repo, created_at=NOW)

        stale = repo.list_created_before(BUSINESS, Microseconds(NOW - 1))
        repo.delete(BUSINESS, oldest.id)
        left = repo.list_created_before(BUSINESS, Microseconds(NOW - 1))

    assert [upload.id for upload in stale] == [oldest.id, older.id]
    assert [upload.id for upload in left] == [older.id]
