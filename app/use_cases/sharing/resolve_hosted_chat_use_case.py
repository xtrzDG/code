from app.contracts.repositories.sharing_repositories import (
    PublicSlugClaimRepoContract,
)
from app.contracts.storage import StorageScopeContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.public_slugs import PublicSlugClaimDocument
from app.schemas.dto.sharing import HostedChatLookup
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId

UNAVAILABLE_MESSAGE: str = "This chat is not available."


class ResolveHostedChatUseCase(UseCaseContract[HostedChatLookup, BusinessId]):
    """
    The business a visitor's /c/{address} belongs to: the business that
    took the slug (any slug it ever had), or the business id itself for a
    business without an address yet. An unknown address is not found.

    The visitor's page runs before the business is known, so this one read
    of a claim by its key looks across businesses explicitly.
    """

    def __init__(
        self,
        public_slug_claim_repo: PublicSlugClaimRepoContract,
        storage_scope: StorageScopeContract,
    ) -> None:
        self._public_slug_claim_repo: PublicSlugClaimRepoContract = (
            public_slug_claim_repo
        )
        self._storage_scope: StorageScopeContract = storage_scope

    def run(self, input_data: HostedChatLookup) -> BusinessId:
        if input_data.slug is not None:
            with self._storage_scope.platform_wide():
                claim: PublicSlugClaimDocument | None = (
                    self._public_slug_claim_repo.get(input_data.slug)
                )
            if claim is None:
                raise NotFoundError(UNAVAILABLE_MESSAGE)

            return claim.business_id

        if input_data.requested_business_id is not None:
            return input_data.requested_business_id

        raise NotFoundError(UNAVAILABLE_MESSAGE)
