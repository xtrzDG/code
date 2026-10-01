from app.contracts.repositories import BusinessProfileRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.businesses import BusinessLinkKind
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.knowledge import SendLinkQuery, SendLinkResult


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

        for link in profile.links:
            if link.kind is input_data.kind:
                return SendLinkResult(kind=input_data.kind, url=link.url)

        if input_data.kind is BusinessLinkKind.MAP and profile.address is not None:
            return SendLinkResult(kind=input_data.kind, url=profile.address.maps_url)

        return SendLinkResult(kind=input_data.kind)
