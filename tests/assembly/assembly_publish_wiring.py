"""Go-live readiness, publish, rollback, apply changes and the assemble pipelines."""

from app.orchestrators.assistants.apply_changes_orchestrator import (
    ApplyChangesOrchestrator,
)
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.assistants.assemble_assistant_version_pipeline import (
    AssembleAssistantVersionPipeline,
)
from app.use_cases.assistants.activate_assistant_version_use_case import (
    ActivateAssistantVersionUseCase,
)
from app.use_cases.assistants.apply.check_applied_version_use_case import (
    CheckAppliedVersionUseCase,
)
from app.use_cases.assistants.apply.describe_apply_changes_use_case import (
    DescribeApplyChangesUseCase,
)
from app.use_cases.assistants.apply.fail_apply_changes_use_case import (
    FailApplyChangesUseCase,
)
from app.use_cases.assistants.apply.get_apply_changes_use_case import (
    GetApplyChangesUseCase,
)
from app.use_cases.assistants.apply.publish_applied_version_use_case import (
    PublishAppliedVersionUseCase,
)
from app.use_cases.assistants.apply.select_smoke_checks_use_case import (
    SelectSmokeChecksUseCase,
)
from app.use_cases.assistants.apply.start_apply_changes_use_case import (
    StartApplyChangesUseCase,
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
from app.use_cases.billing.start_trial_at_go_live_use_case import (
    StartTrialAtGoLiveUseCase,
)
from app.use_cases.setup.record_activation_event_use_case import (
    RecordActivationEventUseCase,
)
from app.use_cases.voice.remove_voice_agent_use_case import RemoveVoiceAgentUseCase
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from tests.analytics.recording_product_events import RecordingProductEvents
from tests.assembly.assembly_autotest_wiring import AssemblyAutotestWiring
from tests.live_events.recording_event_publisher import RecordingEventPublisher


class AssemblyPublishWiring(AssemblyAutotestWiring):
    """
    The autotest wiring with go-live readiness, publish, rollback (the
    first go-live starts the trial and is a milestone) and "Apply changes".
    """

    def _build_publish_use_cases(self) -> None:
        self.product_events = RecordingProductEvents()
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
            plan_registry=self.plan_registry,
            voice_agent_provisioner=self.voice_provisioner,
            app_settings=self.settings,
            wall_clock=self.wall_clock,
        )
        self.get_readiness_use_case = GetGoLiveReadinessUseCase(
            authorize,
            self.version_repo,
            check_readiness,
        )
        self.record_event_use_case = RecordActivationEventUseCase(
            self.activation_event_repo,
            self.wall_clock,
            product_events=self.product_events,
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
            start_trial_at_go_live=StartTrialAtGoLiveUseCase(
                self.subscription_repo,
                self.invoice_repo,
                self.plan_registry,
                self.wall_clock,
                product_events=self.product_events,
            ),
            record_activation_event=self.record_event_use_case,
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
        self._build_apply_use_cases()

    def _build_apply_use_cases(self) -> None:
        self.apply_events = RecordingEventPublisher()
        self.publish_applied_use_case = PublishAppliedVersionUseCase(
            self.apply_repo,
            self.version_repo,
            self.run_repo,
            self.business_repo,
            self.activate_use_case,
            self.audit_repo,
            self.apply_events,
            self.wall_clock,
            product_events=self.product_events,
        )
        self.publish_applied_later.target = self.publish_applied_use_case
        self.describe_apply_use_case = DescribeApplyChangesUseCase(
            self.apply_repo,
            self.version_repo,
            self.run_repo,
            self.profile_repo,
            self.collect_pending_changes_use_case,
            LocalizedTextResolver(),
        )
        self.get_apply_use_case = GetApplyChangesUseCase(
            self.authorize, self.describe_apply_use_case
        )
        self.select_smoke_checks_use_case = SelectSmokeChecksUseCase(
            self.business_repo,
            self.version_repo,
            self.knowledge_repo,
            self.niche_registry,
            self.wall_clock,
        )
        self.apply_changes_orchestrator = ApplyChangesOrchestrator(
            start_apply_changes=StartApplyChangesUseCase(
                self.authorize,
                self.apply_repo,
                self.version_repo,
                self.profile_repo,
                self.collect_pending_changes_use_case,
                self.audit_repo,
                self.apply_events,
                self.wall_clock,
            ),
            assemble_assistant_version=self.assemble_use_case,
            check_applied_version=CheckAppliedVersionUseCase(
                self.apply_repo,
                self.version_repo,
                self.business_repo,
                self.check_readiness_use_case,
                self.apply_events,
                self.wall_clock,
                product_events=self.product_events,
            ),
            select_smoke_checks=self.select_smoke_checks_use_case,
            start_autotest_run=self.start_autotest_run_use_case,
            enqueue_autotest_run=self.enqueue_autotest_run_use_case,
            publish_applied_version=self.publish_applied_use_case,
            fail_apply_changes=FailApplyChangesUseCase(
                self.apply_repo,
                self.apply_events,
                self.wall_clock,
                product_events=self.product_events,
            ),
            get_apply_changes=self.get_apply_use_case,
        )
