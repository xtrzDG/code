from app.contracts.repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
    ChannelRepoContract,
    KnowledgeItemRepoContract,
    ResourceRepoContract,
    ScheduleExceptionRepoContract,
)
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.demo_data import DemoBusinessFoundation, DemoChannelCredential
from app.schemas.typings.businesses.prefixed_id import BusinessId


class StoreDemoFoundationUseCase(UseCaseContract[DemoBusinessFoundation, BusinessId]):
    """
    Store what the owner of a demo business set up: the business with its
    team and staff contacts, the completed profile, knowledge, bookable
    resources, special days and connected channels. Made-up channel
    credentials are encrypted like real ones; no provider is called.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        resource_repo: ResourceRepoContract,
        schedule_exception_repo: ScheduleExceptionRepoContract,
        channel_repo: ChannelRepoContract,
        secret_cipher: SecretCipherAdapterContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._schedule_exception_repo: ScheduleExceptionRepoContract = (
            schedule_exception_repo
        )
        self._channel_repo: ChannelRepoContract = channel_repo
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher

    def run(self, input_data: DemoBusinessFoundation) -> BusinessId:
        self._business_repo.save(input_data.business)
        self._business_profile_repo.save(input_data.profile)
        for item in input_data.knowledge_items:
            self._knowledge_item_repo.save(item)

        for resource in input_data.resources:
            self._resource_repo.save(resource)

        for exception in input_data.schedule_exceptions:
            self._schedule_exception_repo.save(exception)

        for channel in input_data.channels:
            self._channel_repo.save(
                self._with_credential(channel, input_data.channel_credentials)
            )

        return input_data.business.id

    def _with_credential(
        self,
        channel: ChannelDocument,
        credentials: list[DemoChannelCredential],
    ) -> ChannelDocument:
        for credential in credentials:
            if credential.channel is channel.kind:
                channel.encrypted_secret = self._secret_cipher.encrypt(
                    credential.secret
                )

        return channel
