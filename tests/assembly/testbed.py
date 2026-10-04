"""In-memory wiring of the assembly slice, shared by its tests.

Everything the slice depends on is either an in-memory repository or a
fake; the AI customer and the judge are ScriptedLlmAdapter instances whose
answers tests can program per scenario key. The wiring is layered:
assembly_store (repositories) -> assembly_scripted_models (fakes and
scripted models) -> assembly_autotest_wiring -> assembly_publish_wiring.
"""

from collections.abc import Mapping, Sequence

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateways.http.assistant_routes import build_assistant_router
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.user_authentication import build_current_user_dependency
from app.gateways.worker.background_worker import WorkerTickReport
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.schemas.dto.assistants.assembly_sources import LlmTokenPrice
from app.schemas.dto.assistants.assistant_commands import (
    AssembleAssistantVersionCommand,
    AssembleAssistantVersionRequest,
    PublishAssistantVersionCommand,
    RunAutotestsCommand,
)
from app.schemas.dto.assistants.assistant_views import (
    AssistantVersionDetails,
    AutotestRunView,
)
from app.schemas.typings.assistants.constrained_integers import (
    PriceQuestionScenarioLimit,
)
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from tests.assembly.assembly_publish_wiring import AssemblyPublishWiring


class AssemblyTestbed(AssemblyPublishWiring):
    """
    The slice wired over in-memory repositories, with fakes for registries,
    the conversation engine, the voice platform and the call greeting.

    Program the autotests through:
    - `customer_script` (default: one message in the scenario language, then
      [DONE]);
    - `reply_scripts[scenario_key]` (default: `default_reply_script`);
    - `judge_scores[scenario_key]` and `judge_raw_answers[scenario_key]`
      (default: 5 on every criterion).
    """

    def __init__(
        self,
        environment: Mapping[str, str] | None = None,
        price_question_limit: int = 10,
        llm_token_prices: Sequence[LlmTokenPrice] = (),
        customer_token_usage: tuple[int, int] | None = None,
        judge_token_usage: tuple[int, int] | None = None,
        reply_cost: int = 0,
    ) -> None:
        super().__init__(
            environment, customer_token_usage, judge_token_usage, reply_cost
        )
        self._build_autotest_use_cases(
            PriceQuestionScenarioLimit(price_question_limit),
            llm_token_prices,
        )
        self._build_publish_use_cases()

    # Shortcuts used by tests.

    def assemble(
        self,
        business_id: BusinessId,
        run_autotests: bool = False,
        user_id: UserId | None = None,
    ) -> AssistantVersionDetails:
        self.advance(60)
        return self.assemble_pipeline.start(
            AssembleAssistantVersionCommand(
                user_id=user_id or self.owner_id,
                business_id=business_id,
                request=AssembleAssistantVersionRequest(run_autotests=run_autotests),
            )
        )

    def run_autotests(
        self,
        business_id: BusinessId,
        version_id: AssistantVersionId,
        user_id: UserId | None = None,
    ) -> AutotestRunView:
        self.advance(60)
        return self.run_autotests_orchestrator.execute(
            RunAutotestsCommand(
                user_id=user_id or self.owner_id,
                business_id=business_id,
                version_id=version_id,
            )
        )

    def publish(
        self,
        business_id: BusinessId,
        version_id: AssistantVersionId,
        accept_failed_tests: bool = False,
        user_id: UserId | None = None,
    ) -> AssistantVersionDetails:
        self.advance(60)
        return self.publish_use_case.run(
            PublishAssistantVersionCommand(
                user_id=user_id or self.owner_id,
                business_id=business_id,
                version_id=version_id,
                accept_failed_tests=accept_failed_tests,
            )
        )

    def run_worker(self) -> WorkerTickReport:
        """One worker tick: plays every queued autotest run."""

        self.advance(60)
        return self.worker.run_once()

    def build_client(self) -> TestClient:
        http_application = FastAPI()
        install_error_handlers(http_application)
        http_application.include_router(
            build_assistant_router(
                assemble_assistant_version_operator=PipelineOperator(
                    self.queued_assemble_pipeline
                ),
                list_assistant_versions_operator=PipelineOperator(
                    OrchestratorPipeline(
                        UseCaseOrchestrator(self.list_versions_use_case)
                    )
                ),
                get_assistant_version_operator=PipelineOperator(
                    OrchestratorPipeline(UseCaseOrchestrator(self.get_version_use_case))
                ),
                get_autotest_run_operator=PipelineOperator(
                    OrchestratorPipeline(
                        UseCaseOrchestrator(self.get_autotest_run_use_case)
                    )
                ),
                get_go_live_readiness_operator=PipelineOperator(
                    OrchestratorPipeline(
                        UseCaseOrchestrator(self.get_readiness_use_case)
                    )
                ),
                run_autotests_operator=PipelineOperator(
                    OrchestratorPipeline(self.queue_autotest_run_orchestrator)
                ),
                publish_assistant_version_operator=PipelineOperator(
                    OrchestratorPipeline(UseCaseOrchestrator(self.publish_use_case))
                ),
                rollback_assistant_version_operator=PipelineOperator(
                    OrchestratorPipeline(UseCaseOrchestrator(self.rollback_use_case))
                ),
                current_user=build_current_user_dependency(
                    self.authentication, SessionAssuranceContext()
                ),
            )
        )
        return TestClient(http_application)

    def bearer(self, user_id: UserId) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.authentication.register(user_id)}"}
