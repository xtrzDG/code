from app.contracts.repositories.integration_repositories import ApiKeyRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.integrations import ApiKeyScope
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.integrations.api_key_views import ApiKeyList, ApiKeysQuery
from app.schemas.typings.integrations.constrained_integers import (
    PublicApiRequestsPerMinute,
)
from app.use_cases.integrations.api_key_records import MAX_API_KEYS, api_key_view


class ListApiKeysUseCase(UseCaseContract[ApiKeysQuery, ApiKeyList]):
    """
    Settings → Integrations → API keys: the business's keys, newest first
    (revoked ones stay listed, greyed), the scopes a key may get and the
    per-key request limit. Owners only; no secret is ever shown again.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        api_key_repo: ApiKeyRepoContract,
        requests_per_minute: PublicApiRequestsPerMinute,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._api_key_repo: ApiKeyRepoContract = api_key_repo
        self._requests_per_minute: PublicApiRequestsPerMinute = requests_per_minute

    def run(self, input_data: ApiKeysQuery) -> ApiKeyList:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        return ApiKeyList(
            items=[
                api_key_view(api_key)
                for api_key in self._api_key_repo.list_by_business(business.id)
            ],
            scopes=list(ApiKeyScope),
            max_keys=MAX_API_KEYS,
            requests_per_minute=self._requests_per_minute,
        )
