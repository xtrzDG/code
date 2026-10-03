from app.contracts.repositories.business_repositories import BusinessProfileRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.knowledge import SendLinkQuery, SendLinkResult
from app.utilities.knowledge.profile_links import find_profile_link


class SendLinkUseCase(UseCaseContract[SendLinkQuery, SendLinkResult]):
    """
    Model tool send_link: a link of the requested kind from the profile only.

    A map request falls back to the maps link of the address. Without such a
    link the result has no URL, and the assistant must not make one up.
    """

    def __init__(self, business_profile_repo: BusinessProfileRepoContract) -> None:
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo

    def run(self, input_data: SendLinkQuery) -> SendLinkResult:
        profile: BusinessProfileDocument | None = (
            self._business_profile_repo.get_by_business(input_data.business_id)
        )
        if profile is None:
            return SendLinkResult(kind=input_data.kind)

        return SendLinkResult(
            kind=input_data.kind, url=find_profile_link(profile, input_data.kind)
        )
