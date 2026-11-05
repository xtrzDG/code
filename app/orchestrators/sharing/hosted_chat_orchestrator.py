from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.storage import StorageScopeContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.sharing import HostedChatLookup, HostedChatView
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.observability.log_context import bound_log_context


class HostedChatOrchestrator(OrchestratorContract[HostedChatLookup, HostedChatView]):
    """
    A visitor opens a business's hosted chat page: find the business by
    the page's address, then read what the page needs inside that
    business's storage scope (row-level security on Postgres), like every
    other request for one business.
    """

    def __init__(
        self,
        resolve_hosted_chat: UseCaseContract[HostedChatLookup, BusinessId],
        get_hosted_chat: UseCaseContract[BusinessId, HostedChatView],
        storage_scope: StorageScopeContract,
    ) -> None:
        self._resolve_hosted_chat: UseCaseContract[HostedChatLookup, BusinessId] = (
            resolve_hosted_chat
        )
        self._get_hosted_chat: UseCaseContract[BusinessId, HostedChatView] = (
            get_hosted_chat
        )
        self._storage_scope: StorageScopeContract = storage_scope

    def execute(self, input_data: HostedChatLookup) -> HostedChatView:
        business_id: BusinessId = self._resolve_hosted_chat.run(input_data)
        with (
            bound_log_context(business_id=business_id),
            self._storage_scope.scoped_to_business(business_id),
        ):
            return self._get_hosted_chat.run(business_id)
