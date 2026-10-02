from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.channels.channel_settings import ChannelListQuery, ChannelView
from app.use_cases.channels.channel_views import (
    build_channel_view,
    sort_channel_views,
)


class ListChannelsUseCase(UseCaseContract[ChannelListQuery, list[ChannelView]]):
    """
    Channels of a business for its owners and staff, free messengers first.
    Channels never connected are absent; credentials are never returned.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        channel_repo: ChannelRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._channel_repo: ChannelRepoContract = channel_repo

    def run(self, input_data: ChannelListQuery) -> list[ChannelView]:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        return sort_channel_views(
            [
                build_channel_view(channel)
                for channel in self._channel_repo.list_by_business(business.id)
            ]
        )
