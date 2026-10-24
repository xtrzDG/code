"""A conversation's quality score on its card in the cabinet."""

from app.contracts.repositories.quality_repositories import (
    ConversationQualityRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversation_quality import ConversationQualityScoreDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.quality import ConversationQualityQuery, ConversationQualityView
from app.utilities.quality.quality_trend import to_score_view


class GetConversationQualityUseCase(
    UseCaseContract[ConversationQualityQuery, ConversationQualityView]
):
    """
    The judge's score of one conversation (owners and staff): the five
    criteria and the notes in the owner's language, or no score when the
    nightly sample did not pick it. Judged on a transcript without contact
    details; the notes never quote the customer, so reading them is not an
    audited view of personal data.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        conversation_quality_repo: ConversationQualityRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._quality_repo: ConversationQualityRepoContract = conversation_quality_repo

    def run(self, input_data: ConversationQualityQuery) -> ConversationQualityView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        score: ConversationQualityScoreDocument | None = self._quality_repo.get(
            business.id, input_data.conversation_id
        )
        return ConversationQualityView(
            conversation_id=input_data.conversation_id,
            score=None if score is None else to_score_view(score),
        )
