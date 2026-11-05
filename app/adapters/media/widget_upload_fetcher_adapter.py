from app.contracts.channel_media import ChannelMediaFetcherContract
from app.contracts.media_storage import MediaStorageAdapterContract
from app.schemas.dto.media import (
    ChannelMediaRequest,
    FetchedMedia,
    MediaLocation,
    StoredMediaFile,
)
from app.schemas.exceptions.media_errors import (
    MediaTooLargeError,
    MediaUnavailableError,
)
from app.schemas.typings.media.strings import MediaStoragePath, ProviderMediaType
from app.utilities.media.media_paths import is_widget_upload_path


class WidgetUploadFetcherAdapter(ChannelMediaFetcherContract):
    """
    The files of website chat messages: the visitor uploaded them before
    the message, so the "platform" that keeps them is the platform's own
    media storage (`provider_media_id` is the upload's storage path, under
    its business's directory; any other path is not handed out). The bytes
    were checked when they came; the worker stores its own copy for the
    message, with the business's retention.
    """

    def __init__(self, media_storage: MediaStorageAdapterContract) -> None:
        self._media_storage: MediaStorageAdapterContract = media_storage

    def fetch(self, request: ChannelMediaRequest) -> FetchedMedia:
        path: str = str(request.provider_media_id)
        if request.business_id is None or not is_widget_upload_path(
            request.business_id, path
        ):
            raise MediaUnavailableError("The website chat hands out only its uploads.")

        stored: StoredMediaFile | None = self._media_storage.read(
            MediaLocation(business_id=request.business_id, path=MediaStoragePath(path))
        )
        if stored is None:
            raise MediaUnavailableError("The upload is gone (purged after a day).")

        if len(stored.content) > int(request.max_bytes):
            raise MediaTooLargeError("The upload is larger than its kind's cap.")

        return FetchedMedia(
            content=stored.content,
            declared_type=ProviderMediaType(str(stored.media_type)),
        )
