"""
The activation follow-up's records (migration 1080): the nudges each
business was sent and its done-for-you setup request, both keyed by ids
derived from the business, so each exists once.
"""

from app.contracts.repositories.billing_repositories import (
    OnboardingRequestRepoContract,
)
from app.contracts.repositories.setup_repositories import NudgeSentRepoContract
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.schemas.constants.nudges import NudgeCode
from app.schemas.domain.billing import OnboardingRequestDocument
from app.schemas.domain.setup import NudgeSentDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.billing.onboarding_keys import derive_onboarding_request_id
from app.utilities.setup.setup_keys import derive_nudge_sent_id


class NudgeSentRepository(
    BusinessScopedRepository[NudgeSentDocument],
    NudgeSentRepoContract,
):
    """Sent nudges keyed by their derived id: one per business and code."""

    def find(
        self, business_id: BusinessId, code: NudgeCode
    ) -> NudgeSentDocument | None:
        return self._load(business_id, str(derive_nudge_sent_id(business_id, code)))

    def record_once(self, nudge: NudgeSentDocument) -> bool:
        return bool(self._collection.insert_if_absent(str(nudge.id), nudge))


class OnboardingRequestRepository(
    BusinessScopedRepository[OnboardingRequestDocument],
    OnboardingRequestRepoContract,
):
    """Done-for-you setup requests keyed by their derived id: one per business."""

    def get_by_business(
        self, business_id: BusinessId
    ) -> OnboardingRequestDocument | None:
        return self._load(business_id, str(derive_onboarding_request_id(business_id)))

    def open_once(self, request: OnboardingRequestDocument) -> bool:
        return bool(self._collection.insert_if_absent(str(request.id), request))

    def save(self, request: OnboardingRequestDocument) -> None:
        self._store(str(request.id), request)
