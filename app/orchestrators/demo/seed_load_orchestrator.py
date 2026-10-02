import logging

from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.assistants.assistant_commands import (
    AssembleAssistantVersionCommand,
)
from app.schemas.dto.assistants.assistant_views import AssistantVersionDetails
from app.schemas.dto.demo_data import DemoActivityStorage, DemoBusinessFoundation
from app.schemas.dto.load_data import (
    LoadBusinessPlan,
    LoadBusinessSeed,
    LoadSeedManifest,
    LoadSeedPlan,
    LoadVolumeStorage,
    SeedLoadCommand,
)
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId

LOGGER: logging.Logger = logging.getLogger(__name__)
# A progress line every this many businesses (a full run takes minutes).
PROGRESS_EVERY: int = 25


class SeedLoadOrchestrator(OrchestratorContract[SeedLoadCommand, LoadSeedManifest]):
    """
    `workshop seed-load`: a load-test dataset. Owners and plans first,
    then every business exactly like a demo business (its foundation, its
    assistant versions assembled from it as the owner's "assemble" does,
    a month of demo activity with the published version live) and its
    bulk history on top. Returns the manifest the load tests read.
    """

    def __init__(
        self,
        prepare_load_businesses: UseCaseContract[SeedLoadCommand, LoadSeedPlan],
        store_demo_foundation: UseCaseContract[DemoBusinessFoundation, BusinessId],
        assemble_assistant_version: UseCaseContract[
            AssembleAssistantVersionCommand,
            AssistantVersionDetails,
        ],
        store_demo_activity: UseCaseContract[DemoActivityStorage, BusinessId],
        store_load_volume: UseCaseContract[LoadVolumeStorage, LoadBusinessSeed],
    ) -> None:
        self._prepare_load_businesses: UseCaseContract[
            SeedLoadCommand, LoadSeedPlan
        ] = prepare_load_businesses
        self._store_demo_foundation: UseCaseContract[
            DemoBusinessFoundation, BusinessId
        ] = store_demo_foundation
        self._assemble_assistant_version: UseCaseContract[
            AssembleAssistantVersionCommand,
            AssistantVersionDetails,
        ] = assemble_assistant_version
        self._store_demo_activity: UseCaseContract[DemoActivityStorage, BusinessId] = (
            store_demo_activity
        )
        self._store_load_volume: UseCaseContract[
            LoadVolumeStorage, LoadBusinessSeed
        ] = store_load_volume

    def execute(self, input_data: SeedLoadCommand) -> LoadSeedManifest:
        plan: LoadSeedPlan = self._prepare_load_businesses.run(input_data)
        seeds: list[LoadBusinessSeed] = []
        for business_plan in plan.businesses:
            seeds.append(self._store_business(business_plan, plan))
            if len(seeds) % PROGRESS_EVERY == 0 or len(seeds) == len(plan.businesses):
                LOGGER.info(
                    "Load dataset: %d of %d businesses stored.",
                    len(seeds),
                    len(plan.businesses),
                )

        return LoadSeedManifest(seeded_at=plan.seeded_at, businesses=seeds)

    def _store_business(
        self, business_plan: LoadBusinessPlan, plan: LoadSeedPlan
    ) -> LoadBusinessSeed:
        foundation: DemoBusinessFoundation = business_plan.foundation
        business_id: BusinessId = self._store_demo_foundation.run(foundation)
        version_ids: list[AssistantVersionId] = [
            self._assemble_assistant_version.run(
                AssembleAssistantVersionCommand(
                    user_id=business_plan.owner_id, business_id=business_id
                )
            ).id
            for _ in foundation.assistant_versions
        ]
        self._store_demo_activity.run(
            DemoActivityStorage(
                foundation=foundation,
                version_ids=version_ids,
                seeded_at=plan.seeded_at,
            )
        )
        return self._store_load_volume.run(
            LoadVolumeStorage(plan=business_plan, seeded_at=plan.seeded_at)
        )
