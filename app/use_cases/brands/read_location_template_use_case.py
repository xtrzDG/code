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
from app.schemas.dto.brands.location_templates import (
    ChannelSettingsTemplate,
    LocationTemplate,
    LocationTemplateQuery,
)


class ReadLocationTemplateUseCase(
    UseCaseContract[LocationTemplateQuery, LocationTemplate]
):
    """
    What a new location takes from this one, for an owner of it (a brand
    owner): the profile, the resources, the knowledge items (menu-import
    drafts left out) and each channel's own settings. Channel accounts and
    tokens, billing, API keys, webhooks and customers stay where they are:
    they are never read here. Runs in this location's storage scope.
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
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._channel_repo: ChannelRepoContract = channel_repo

    def run(self, input_data: LocationTemplateQuery) -> LocationTemplate:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        return LocationTemplate(
            profile=self._business_profile_repo.get_by_business(business.id),
            resources=self._resource_repo.list_by_business(business.id),
            knowledge_items=[
                item
                for item in self._knowledge_item_repo.list_by_business(business.id)
                if item.import_batch_id is None
            ],
            channels=[
                ChannelSettingsTemplate(
                    kind=channel.kind,
                    web_chat_appearance=channel.web_chat_appearance,
                    whatsapp_staff_template=channel.whatsapp_staff_template,
                    whatsapp_staff_templates=list(channel.whatsapp_staff_templates),
                )
                for channel in self._channel_repo.list_by_business(business.id)
            ],
        )
