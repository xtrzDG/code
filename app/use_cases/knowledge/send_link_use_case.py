from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.knowledge import SendLinkQuery, SendLinkResult
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.utilities.knowledge.profile_links import find_sendable_link


class SendLinkUseCase(UseCaseContract[SendLinkQuery, SendLinkResult]):
    """
    Model tool send_link: a link of the requested kind from the profile only.

    A map request falls back to the maps link of the address, and a request
    for the privacy notice to the platform's hosted notice of the business
    when it stored none of its own (the call greeting offers that link to
    every caller). Without such a link the result has no URL, and the
    assistant must not make one up.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        cabinet_base_url: CabinetBaseUrl | None,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._cabinet_base_url: CabinetBaseUrl | None = cabinet_base_url

    def run(self, input_data: SendLinkQuery) -> SendLinkResult:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        profile: BusinessProfileDocument | None = (
            self._business_profile_repo.get_by_business(input_data.business_id)
        )
        if business is None:
            return SendLinkResult(kind=input_data.kind)

        return SendLinkResult(
            kind=input_data.kind,
            url=find_sendable_link(
                business, profile, input_data.kind, self._cabinet_base_url
            ),
        )
