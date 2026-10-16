from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    ChannelRepoContract,
)
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.brands.location_templates import LocationTemplateWrite
from app.utilities.brands.location_copies import LocationCopies, copy_location


class WriteLocationTemplateUseCase(UseCaseContract[LocationTemplateWrite, None]):
    """
    Fill a new location from a template, for its owner, in its own storage
    scope: its own copies of the profile, resources and knowledge (new
    ids, links mapped) and channels waiting for its own accounts
    (`app/utilities/brands/location_copies.py`).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        business_profile_repo: BusinessProfileRepoContract,
        resource_repo: ResourceRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        channel_repo: ChannelRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: LocationTemplateWrite) -> None:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        copies: LocationCopies = copy_location(
            input_data.template, business.id, self._wall_clock.now_unix()
        )
        if copies.profile is not None:
            self._business_profile_repo.save(copies.profile)

        for resource in copies.resources:
            self._resource_repo.save(resource)

        for item in copies.knowledge_items:
            self._knowledge_item_repo.save(item)

        for channel in copies.channels:
            self._channel_repo.save(channel)
