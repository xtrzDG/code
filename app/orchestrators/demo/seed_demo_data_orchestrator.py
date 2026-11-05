from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.assistants.assistant_commands import (
    AssembleAssistantVersionCommand,
)
from app.schemas.dto.assistants.assistant_views import AssistantVersionDetails
from app.schemas.dto.demo_data import (
    DemoActivityStorage,
    DemoBusinessFoundation,
    DemoDataSeedReport,
    DemoSeedPlan,
    SeedDemoDataCommand,
)
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId


class SeedDemoDataOrchestrator(
    OrchestratorContract[SeedDemoDataCommand, DemoDataSeedReport]
):
    """
    Development demo data (SEED_DEMO_DATA), once: the demo accounts, then
    for every demo business the owner does not have yet its foundation,
    its assistant versions assembled from it exactly as the owner's
    "assemble" does (without autotests or provider calls), and its month of
    activity pinned to those versions.
    """

    def __init__(
        self,
        prepare_demo_accounts: UseCaseContract[SeedDemoDataCommand, DemoSeedPlan],
        store_demo_foundation: UseCaseContract[DemoBusinessFoundation, BusinessId],
        assemble_assistant_version: UseCaseContract[
            AssembleAssistantVersionCommand,
            AssistantVersionDetails,
        ],
        store_demo_activity: UseCaseContract[DemoActivityStorage, BusinessId],
    ) -> None:
        self._prepare_demo_accounts: UseCaseContract[
            SeedDemoDataCommand, DemoSeedPlan
        ] = prepare_demo_accounts
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

    def execute(self, input_data: SeedDemoDataCommand) -> DemoDataSeedReport:
        plan: DemoSeedPlan = self._prepare_demo_accounts.run(input_data)
        created_business_ids: list[BusinessId] = []
        for foundation in plan.foundations:
            business_id: BusinessId = self._store_demo_foundation.run(foundation)
            version_ids: list[AssistantVersionId] = [
                self._assemble_assistant_version.run(
                    AssembleAssistantVersionCommand(
                        user_id=plan.owner_id, business_id=business_id
                    )
                ).id
                for _ in foundation.assistant_versions
            ]
            created_business_ids.append(
                self._store_demo_activity.run(
                    DemoActivityStorage(
                        foundation=foundation,
                        version_ids=version_ids,
                        seeded_at=plan.seeded_at,
                    )
                )
            )

        return DemoDataSeedReport(
            owner_id=plan.owner_id,
            created_business_ids=created_business_ids,
            kept_business_ids=plan.kept_business_ids,
        )
