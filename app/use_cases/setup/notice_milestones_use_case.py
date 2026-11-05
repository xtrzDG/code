"""Periodic job: notice and announce the milestones of live businesses."""

import logging

from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.domain.setup import SetupStateDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.setup.setup_guide import GuideProgressCheck
from app.schemas.dto.setup.setup_progress import ActivationMilestoneCheck
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.shared.business_walk import walk_businesses

logger: logging.Logger = logging.getLogger(__name__)


class NoticeMilestonesUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Every few minutes, over the businesses whose assistant answers
    customers: notice the first real conversation, the first booking and the
    first booking after hours as soon as they happen, so the team's phones
    hear about them (the cabinet celebrates them on its next look) even
    while nobody has the cabinet open. Each is announced once: it is stored
    once, and its alert names it. A business with every milestone already
    stored costs one read of its milestones and one of its setup state; one
    failing business never stops the others.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        record_activation_milestones: UseCaseContract[ActivationMilestoneCheck, None],
        notice_guide_progress: UseCaseContract[
            GuideProgressCheck, SetupStateDocument | None
        ],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._record_activation_milestones: UseCaseContract[
            ActivationMilestoneCheck, None
        ] = record_activation_milestones
        self._notice_guide_progress: UseCaseContract[
            GuideProgressCheck, SetupStateDocument | None
        ] = notice_guide_progress

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        checked: int = 0
        for business in walk_businesses(self._business_repo):
            if (
                business.status is not BusinessStatus.LIVE
                or business.published_assistant_version_id is None
            ):
                continue

            try:
                # The owner's own test first: it is no customer to announce.
                self._notice_guide_progress.run(
                    GuideProgressCheck(business=business, is_live=True)
                )
                self._record_activation_milestones.run(
                    ActivationMilestoneCheck(business_id=business.id)
                )
                checked += 1
            except Exception:
                logger.exception("Milestones of business %s failed.", business.id)

        return JobReport(processed_count=ProcessedItemCount(checked))
