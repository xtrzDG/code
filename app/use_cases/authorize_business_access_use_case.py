from app.contracts.repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.exceptions.application_errors import NotFoundError


class AuthorizeBusinessAccessUseCase(
    UseCaseContract[BusinessAccessRequest, BusinessDocument]
):
    """
    Return the business when the owner owns it.

    Another owner's business is reported as missing, not forbidden, so ids of
    foreign businesses cannot be probed.
    """

    def __init__(self, business_repo: BusinessRepoContract) -> None:
        self._business_repo: BusinessRepoContract = business_repo

    def run(self, input_data: BusinessAccessRequest) -> BusinessDocument:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None or business.owner_id != input_data.owner_id:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        return business
