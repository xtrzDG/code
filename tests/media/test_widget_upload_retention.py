"""
Website uploads after their message: the worker reads only this business's
upload paths from the media storage, and the daily retention job deletes
every upload older than a day (file and record, audited) while the copy the
message keeps stays for the business's retention.
"""

import pytest
from typed_time_provider import Microseconds

from app.adapters.media.widget_upload_fetcher_adapter import (
    WidgetUploadFetcherAdapter,
)
from app.gateways.http.middleware.body_size_limit_middleware import (
    WIDGET_UPLOAD_BODY_LIMIT_BYTES,
    find_body_limit,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.compliance import PurgeExpiredRecordingsCommand
from app.schemas.dto.media import ChannelMediaRequest, MediaLocation, StoredMediaFile
from app.schemas.exceptions.media_errors import (
    MediaTooLargeError,
    MediaUnavailableError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.media.constrained_integers import MediaByteLimit
from app.schemas.typings.media.constrained_strings import MessageMediaType
from app.schemas.typings.media.prefixed_id import WidgetUploadId
from app.schemas.typings.media.strings import MediaStoragePath, ProviderMediaId
from app.use_cases.compliance.purge_stale_widget_uploads_use_case import (
    PurgeStaleWidgetUploadsUseCase,
)
from app.utilities.media.media_paths import widget_upload_storage_path
from tests.channels.widget_upload_bed import WidgetUploadBed
from tests.media.media_fakes import InMemoryMediaStorage
from tests.media.upload_files import png_photo

BUSINESS: BusinessId = BusinessId()
OTHER_BUSINESS: BusinessId = BusinessId()
PNG: MessageMediaType = MessageMediaType("image/png")
HOUR_SECONDS: int = 60 * 60


def fetch_request(
    path: str, business_id: BusinessId | None = BUSINESS, max_bytes: int = 4096
) -> ChannelMediaRequest:
    return ChannelMediaRequest(
        channel=ChannelKind.WEB_CHAT,
        provider_media_id=ProviderMediaId(path),
        max_bytes=MediaByteLimit(max_bytes),
        business_id=business_id,
    )


class TestTheFetcher:
    def storage_with_upload(self) -> tuple[InMemoryMediaStorage, MediaStoragePath]:
        storage = InMemoryMediaStorage()
        path = widget_upload_storage_path(BUSINESS, WidgetUploadId(), PNG)
        storage.store(
            MediaLocation(business_id=BUSINESS, path=path),
            StoredMediaFile(content=png_photo(), media_type=PNG),
        )
        return storage, path

    def test_an_upload_of_the_business_is_read(self) -> None:
        storage, path = self.storage_with_upload()

        fetched = WidgetUploadFetcherAdapter(storage).fetch(fetch_request(str(path)))

        assert fetched.content == png_photo()
        assert fetched.declared_type == "image/png"

    @pytest.mark.parametrize(
        "path",
        [
            "message-media/{business}/file.png",
            "widget-uploads/{other}/file.png",
            "widget-uploads/{business}/../{other}/file.png",
            "widget-uploads/{business}/",
            "widget-uploads/{business}/nested/file.png",
        ],
    )
    def test_no_other_path_is_handed_out(self, path: str) -> None:
        storage, _ = self.storage_with_upload()
        named = path.format(business=BUSINESS, other=OTHER_BUSINESS)

        with pytest.raises(MediaUnavailableError):
            WidgetUploadFetcherAdapter(storage).fetch(fetch_request(named))

    def test_a_request_without_a_business_or_a_purged_file_is_refused(self) -> None:
        storage, path = self.storage_with_upload()
        fetcher = WidgetUploadFetcherAdapter(storage)
        storage.files.clear()

        with pytest.raises(MediaUnavailableError):
            fetcher.fetch(fetch_request(str(path), business_id=None))
        with pytest.raises(MediaUnavailableError):
            fetcher.fetch(fetch_request(str(path)))

    def test_a_file_over_the_kind_cap_is_refused(self) -> None:
        storage, path = self.storage_with_upload()
        storage.store(
            MediaLocation(business_id=BUSINESS, path=path),
            StoredMediaFile(content=png_photo() + bytes(2048), media_type=PNG),
        )

        with pytest.raises(MediaTooLargeError):
            WidgetUploadFetcherAdapter(storage).fetch(
                fetch_request(str(path), max_bytes=1024)
            )


class TestTheDailyPurge:
    def test_uploads_older_than_a_day_go_with_their_files(self) -> None:
        bed = WidgetUploadBed()
        testbed = bed.testbed
        sent_id = bed.uploaded_id(png_photo(), "image/png")
        assert bed.send([sent_id], "photo").status_code == 202
        testbed.run_worker()
        kept_copies = len(testbed.media_storage.files) - 1
        testbed.clock.advance(23 * HOUR_SECONDS)
        fresh_id = bed.uploaded_id(png_photo(), "image/png")
        testbed.clock.advance(2 * HOUR_SECONDS)
        purge = PurgeStaleWidgetUploadsUseCase(
            testbed.business_repo,
            testbed.widget_upload_repo,
            testbed.media_storage,
            testbed.audit_log_repo,
            testbed.wall_clock,
        )

        first = purge.run(PurgeExpiredRecordingsCommand(business_id=None))
        second = purge.run(PurgeExpiredRecordingsCommand(business_id=bed.business.id))

        assert (int(first.deleted_files), int(second.deleted_files)) == (1, 0)
        assert (
            testbed.widget_upload_repo.get_many(
                bed.business.id, [WidgetUploadId(sent_id)]
            )
            == []
        )
        assert bed.stored_upload(fresh_id).attached_at is None
        # The message's own copy and the fresh upload stay.
        assert len(testbed.media_storage.files) == kept_copies + 1
        assert ("retention_purge", "widget_upload") in testbed.audit_actions(
            bed.business.id
        )

    def test_nothing_older_than_a_day_means_nothing_purged(self) -> None:
        bed = WidgetUploadBed()
        bed.uploaded_id(png_photo(), "image/png")
        testbed = bed.testbed
        purge = PurgeStaleWidgetUploadsUseCase(
            testbed.business_repo,
            testbed.widget_upload_repo,
            testbed.media_storage,
            testbed.audit_log_repo,
            testbed.wall_clock,
        )

        result = purge.run(PurgeExpiredRecordingsCommand(business_id=None))

        assert int(result.deleted_files) == 0
        assert len(testbed.media_storage.files) == 1
        assert testbed.wall_clock.now_unix() > Microseconds(0)


def test_an_upload_body_may_be_larger_than_a_json_body() -> None:
    assert find_body_limit(f"/v1/widget/{BUSINESS}/attachments") == (
        WIDGET_UPLOAD_BODY_LIMIT_BYTES
    )
    assert find_body_limit(f"/v1/widget/{BUSINESS}/messages") < (
        WIDGET_UPLOAD_BODY_LIMIT_BYTES
    )
