from collections.abc import Mapping

from app.contracts.channel_media import ChannelMediaFetcherContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.media import ChannelMediaRequest, FetchedMedia
from app.schemas.exceptions.media_errors import MediaUnavailableError


class RoutingChannelMediaFetcherAdapter(ChannelMediaFetcherContract):
    """The fetcher of each messaging channel; other channels have no files."""

    def __init__(
        self, fetchers: Mapping[ChannelKind, ChannelMediaFetcherContract]
    ) -> None:
        self._fetchers: dict[ChannelKind, ChannelMediaFetcherContract] = dict(fetchers)

    def fetch(self, request: ChannelMediaRequest) -> FetchedMedia:
        fetcher: ChannelMediaFetcherContract | None = self._fetchers.get(
            request.channel
        )
        if fetcher is None:
            raise MediaUnavailableError(
                f"Files of {request.channel.value} messages cannot be fetched."
            )

        return fetcher.fetch(request)
