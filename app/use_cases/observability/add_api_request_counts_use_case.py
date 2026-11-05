from app.contracts.service_levels import ServiceLevelSlotRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.telemetry import ServiceLevelSeries
from app.schemas.dto.jobs import JobReport
from app.schemas.dto.service_levels import ApiRequestCounts
from app.schemas.typings.observability.constrained_integers import (
    ServiceLevelEventCount,
)
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount


class AddApiRequestCountsUseCase(UseCaseContract[ApiRequestCounts, JobReport]):
    """
    What one API process answered since its last flush, added to the shared
    five-minute slots of the API availability SLI: the requests, and as
    good those answered without a server error (5xx). One atomic write per
    slot, so the processes of every instance add up. The report counts
    the slots written.
    """

    def __init__(self, slot_repo: ServiceLevelSlotRepoContract) -> None:
        self._slot_repo: ServiceLevelSlotRepoContract = slot_repo

    def run(self, input_data: ApiRequestCounts) -> JobReport:
        written: int = 0
        for slot in input_data.slots:
            if int(slot.requests) == 0:
                continue
            self._slot_repo.add(
                ServiceLevelSeries.API_AVAILABILITY,
                slot.slot_start,
                slot.requests,
                ServiceLevelEventCount(
                    max(0, int(slot.requests) - int(slot.server_errors))
                ),
            )
            written += 1
        return JobReport(processed_count=ProcessedItemCount(written))
