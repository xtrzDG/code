from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.public_api.access import PublicApiCall, PublicApiIdentity
from app.schemas.typings.integrations.constrained_integers import (
    PublicApiRequestsPerMinute,
)
from app.use_cases.integrations.public_api.public_access import key_business


class GetPublicIdentityUseCase(UseCaseContract[PublicApiCall, PublicApiIdentity]):
    """
    `GET /v1/public-api/me`: the key's business and what the key may do
    (Zapier's connection test and label). Any valid key may ask.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        requests_per_minute: PublicApiRequestsPerMinute,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._requests_per_minute: PublicApiRequestsPerMinute = requests_per_minute

    def run(self, input_data: PublicApiCall) -> PublicApiIdentity:
        business = key_business(self._business_repo, input_data.principal)
        principal = input_data.principal
        return PublicApiIdentity(
            business_id=business.id,
            business_name=business.name,
            api_key_id=principal.api_key_id,
            api_key_name=principal.api_key_name,
            scopes=principal.scopes,
            requests_per_minute=self._requests_per_minute,
        )
