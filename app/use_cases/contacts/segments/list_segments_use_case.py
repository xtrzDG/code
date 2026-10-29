from app.contracts.repositories.customer_repositories import (
    CustomerSegmentRepoContract,
    CustomerSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.customer_settings import CustomerSettingsDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.customers.customer_segments import SegmentList, SegmentListQuery
from app.use_cases.contacts.segments.segment_support import (
    authorize_owner,
    segment_view,
)


class ListSegmentsUseCase(UseCaseContract[SegmentListQuery, SegmentList]):
    """
    Customers → Segments: the owner's saved segments, the oldest first, and
    the business's tags to build one with. Owners only. The rules only, no
    customer, so the list is not audited.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        segment_repo: CustomerSegmentRepoContract,
        customer_settings_repo: CustomerSettingsRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._segment_repo: CustomerSegmentRepoContract = segment_repo
        self._customer_settings_repo: CustomerSettingsRepoContract = (
            customer_settings_repo
        )

    def run(self, input_data: SegmentListQuery) -> SegmentList:
        business: BusinessDocument = authorize_owner(
            self._authorize_business_access, input_data.user_id, input_data.business_id
        )
        settings: CustomerSettingsDocument | None = (
            self._customer_settings_repo.get_by_business(business.id)
        )
        return SegmentList(
            items=[
                segment_view(segment)
                for segment in self._segment_repo.list_by_business(business.id)
            ],
            known_tags=[] if settings is None else list(settings.known_tags),
        )
