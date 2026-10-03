from app.contracts.repositories.inbox_repositories import (
    QuickReplyLibraryRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.inbox.quick_replies import QuickRepliesQuery, QuickReplyList
from app.use_cases.inbox.quick_replies.quick_reply_views import (
    build_quick_reply_list,
)


class ListQuickRepliesUseCase(UseCaseContract[QuickRepliesQuery, QuickReplyList]):
    """
    The saved replies of a business in the owner's order, for owners (the
    editor) and staff (the picker), with the variables each text uses.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        quick_reply_library_repo: QuickReplyLibraryRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._quick_reply_library_repo: QuickReplyLibraryRepoContract = (
            quick_reply_library_repo
        )

    def run(self, input_data: QuickRepliesQuery) -> QuickReplyList:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        return build_quick_reply_list(
            self._quick_reply_library_repo.get_by_business(business.id)
        )
