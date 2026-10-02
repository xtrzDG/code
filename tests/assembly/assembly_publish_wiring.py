"""Go-live readiness, publish, rollback and assemble pipelines of the testbed."""

from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.assistants.assemble_assistant_version_pipeline import (
    AssembleAssistantVersionPipeline,
)
from app.use_cases.assistants.activate_assistant_version_use_case import (
    ActivateAssistantVersionUseCase,
)
from app.use_cases.assistants.check_go_live_readiness_use_case import (
    CheckGoLiveReadinessUseCase,
)
from app.use_cases.assistants.get_go_live_readiness_use_case import (
    GetGoLiveReadinessUseCase,
)
from app.use_cases.assistants.publish_assistant_version_use_case import (
    PublishAssistantVersionUseCase,
)
from app.use_cases.assistants.rollback_assistant_version_use_case import (
    RollbackAssistantVersionUseCase,
)
from app.use_cases.voice.remove_voice_agent_use_case import RemoveVoiceAgentUseCase
from tests.assembly.assembly_autotest_wiring import AssemblyAutotestWiring


class AssemblyPublishWiring(AssemblyAutotestWiring):
    """The autotest wiring with go-live readiness, publish and rollback."""

    def _build_publish_use_cases(self) -> None:
        authorize = self.authorize
        details_transformer = self.details_transformer
        check_readiness = self.check_readiness_use_case = CheckGoLiveReadinessUseCase(
            subscription_repo=self.subscription_repo,
            dpa_acceptance_repo=self.dpa_repo,
            business_profile_repo=self.profile_repo,
            knowledge_item_repo=self.knowledge_repo,
            resource_repo=self.resource_repo,
            autotest_run_repo=self.run_repo,
            niche_template_registry=self.niche_registry,
            voice_agent_provisioner=self.voice_provisioner,
            app_settings=self.settings,
            wall_clock=self.wall_clock,
        )
        self.get_readiness_use_case = GetGoLiveReadinessUseCase(
            authorize,
            self.version_repo,
            check_readiness,
        )
        activate = self.activate_use_case = ActivateAssistantVersionUseCase(
            check_go_live_readiness=check_readiness,
            remove_voice_agent=RemoveVoiceAgentUseCase(
                self.version_repo,
                self.voice_provisioner,
            ),
            business_profile_repo=self.profile_repo,
            business_repo=self.business_repo,
            assistant_version_repo=self.version_repo,
            voice_agent_provisioner=self.voice_provisioner,
            build_call_greeting=self.call_greeting,
            assistant_tool_catalog=self.tool_catalog,
            app_settings=self.settings,
            wall_clock=self.wall_clock,
        )
        self.publish_use_case = PublishAssistantVersionUseCase(
            authorize,
            self.version_repo,
            check_readiness,
            activate,
            details_transformer,
            self.user_repo,
            self.audit_repo,
            self.wall_clock,
        )
        self.rollback_use_case = RollbackAssistantVersionUseCase(
            authorize,
            self.version_repo,
            activate,
            details_transformer,
        )
        self.assemble_pipeline = AssembleAssistantVersionPipeline(
            UseCaseOrchestrator(self.assemble_use_case),
            self.run_autotests_orchestrator,
            UseCaseOrchestrator(self.get_version_use_case),
        )
        self.queued_assemble_pipeline = AssembleAssistantVersionPipeline(
            UseCaseOrchestrator(self.assemble_use_case),
            self.queue_autotest_run_orchestrator,
            UseCaseOrchestrator(self.get_version_use_case),
        )
