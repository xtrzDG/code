"""
The BACKFILL_STALLED alert's check: post-deploy data tasks that are not
done a day after they became due (the release overlap never ended, a
batch keeps failing, or rows could not be upgraded).
"""

from typed_time_provider import Microseconds

from app.contracts.data_tasks import DataTaskRegistryContract, DataTaskStateRepoContract
from app.schemas.domain.data_tasks import DataTaskStateDocument
from app.schemas.dto.data_tasks import DataTaskDefinition
from app.schemas.dto.platform_alerts import AlertObservation, PlatformAlertRule
from app.schemas.typings.maintenance.constrained_strings import DataTaskKey
from app.schemas.typings.monitoring.constrained_integers import AlertFigure
from app.schemas.typings.monitoring.strings import AlertDetailText
from app.utilities.maintenance.data_task_status import is_stalled, states_by_key

# The detail names at most this many tasks.
NAMED_TASKS: int = 3


class DataTaskAlertChecks:
    """One keyed read of the tasks' states against this release's registry."""

    def __init__(
        self,
        registry: DataTaskRegistryContract,
        state_repo: DataTaskStateRepoContract,
    ) -> None:
        self._registry: DataTaskRegistryContract = registry
        self._state_repo: DataTaskStateRepoContract = state_repo

    def backfill_stalled(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        """Fires when more than `threshold` tasks are stalled."""

        tasks: list[DataTaskDefinition] = self._registry.list_tasks()
        states: dict[DataTaskKey, DataTaskStateDocument] = states_by_key(
            self._state_repo.get_many([task.key for task in tasks])
        )
        stalled: list[DataTaskKey] = [
            task.key for task in tasks if is_stalled(task, states.get(task.key), now)
        ]
        named: str = ", ".join(str(key) for key in stalled[:NAMED_TASKS])
        more: int = len(stalled) - NAMED_TASKS
        detail: str = (
            f"Data tasks not done a day after they became due: {named}"
            f"{f' and {more} more' if more > 0 else ''}. See the system page."
            if stalled
            else "Every post-deploy data task is done or within its first day."
        )
        return AlertObservation(
            code=rule.code,
            figure=AlertFigure(len(stalled)),
            threshold=rule.threshold,
            unit=rule.unit,
            detail=AlertDetailText(detail),
            is_firing=len(stalled) > int(rule.threshold),
        )
