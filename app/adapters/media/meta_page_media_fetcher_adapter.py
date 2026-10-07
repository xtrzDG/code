from app.contracts.channel_media import ChannelMediaFetcherContract
from app.contracts.media_clients import MetaMediaClientContract
from app.schemas.dto.media import ChannelMediaRequest, FetchedMedia
from app.utilities.media.media_hosts import require_meta_media_url


class MetaPageMediaFetcherAdapter(ChannelMediaFetcherContract):
    """
    An attachment of a Messenger or Instagram message: the webhook carries
    its URL on Meta's CDN. Only an https address on a Meta host is fetched
    (the webhook is signed, but the platform never fetches an address a
    payload could point anywhere).
    """

    def __init__(self, meta_media_client: MetaMediaClientContract) -> None:
        self._meta_media_client: MetaMediaClientContract = meta_media_client

    def fetch(self, request: ChannelMediaRequest) -> FetchedMedia:
        return self._meta_media_client.download(
            require_meta_media_url(str(request.provider_media_id)),
            None,
            int(request.max_bytes),
        )
