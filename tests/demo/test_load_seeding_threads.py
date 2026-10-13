"""
`workshop seed-load` stores its businesses on several threads at once,
each in the run's storage scope; the manifest keeps the plan's order, and
a business that fails fails the run.
"""

import threading

import pytest

from app.contracts.storage import StorageScopeContract
from app.contracts.use_case_contract import UseCaseContract
from app.orchestrators.demo.seed_load_orchestrator import SeedLoadOrchestrator
from app.schemas.dto.demo_data import DemoBusinessFoundation
from app.schemas.dto.load_data import LoadSeedManifest, SeedLoadCommand
from app.schemas.typings.businesses.prefixed_id import BusinessId
from tests.e2e.harness import Workshop, start_workshop

COMMAND: SeedLoadCommand = SeedLoadCommand.model_validate(
    {
        "business_count": 2,
        "message_count": 40,
        "booking_count": 4,
        "visitor_count": 2,
        "random_seed": 3,
    }
)


class MeetingFoundations(UseCaseContract[DemoBusinessFoundation, BusinessId]):
    """
    Stores a foundation only once the other business's storing has begun
    too (a barrier: sequential storing would break it, not wait forever),
    or fails for the business named `failing`.
    """

    def __init__(
        self,
        store: UseCaseContract[DemoBusinessFoundation, BusinessId],
        failing: str | None = None,
    ) -> None:
        self._store = store
        self._failing = failing
        self.both_started = threading.Barrier(2, timeout=30)

    def run(self, input_data: DemoBusinessFoundation) -> BusinessId:
        self.both_started.wait()
        if self._failing is not None and str(input_data.business.name).endswith(
            self._failing
        ):
            raise RuntimeError("the second business could not be stored")

        return self._store.run(input_data)


def orchestrator(
    workshop: Workshop, foundations: MeetingFoundations
) -> SeedLoadOrchestrator:
    demo = workshop.container.use_cases.demo
    return SeedLoadOrchestrator(
        prepare_load_businesses=demo.prepare_load_businesses_use_case(),
        store_demo_foundation=foundations,
        assemble_assistant_version=(
            workshop.container.use_cases.assistants.assemble_assistant_version_use_case()
        ),
        store_demo_activity=demo.store_demo_activity_use_case(),
        store_load_volume=demo.store_load_volume_use_case(),
    )


def business_name(workshop: Workshop, business_id: BusinessId) -> str:
    business = workshop.container.repositories.business_repo().get(business_id)
    assert business is not None
    return str(business.name)


def test_businesses_are_stored_at_once_and_listed_in_plan_order() -> None:
    workshop = start_workshop()
    scope: StorageScopeContract = workshop.container.utilities.storage_scope()
    foundations = MeetingFoundations(
        workshop.container.use_cases.demo.store_demo_foundation_use_case()
    )

    with scope.platform_wide():
        manifest: LoadSeedManifest = orchestrator(workshop, foundations).execute(
            COMMAND
        )
        names = [
            business_name(workshop, entry.business_id) for entry in manifest.businesses
        ]

    assert [name.rsplit(" ", 1)[-1] for name in names] == ["1", "2"]
    assert [int(entry.message_count) for entry in manifest.businesses] == [20, 20]


def test_a_business_that_fails_fails_the_run() -> None:
    workshop = start_workshop()
    scope: StorageScopeContract = workshop.container.utilities.storage_scope()
    foundations = MeetingFoundations(
        workshop.container.use_cases.demo.store_demo_foundation_use_case(),
        failing=" 2",
    )

    with (
        scope.platform_wide(),
        pytest.raises(RuntimeError, match="could not be stored"),
    ):
        orchestrator(workshop, foundations).execute(COMMAND)
