from app.containers.meta_connection.meta_connection_dependencies import (
    MetaConnectionDependencies,
)
from app.containers.meta_connection.meta_connection_use_case_factories import (
    MetaConnectionUseCaseFactories,
)
from app.containers.role_chain_factories import business_scoped_operator
from app.contracts.operator_contract import OperatorContract
from app.operators.business_scoped_pipeline_operator import (
    BusinessScopedPipelineOperator,
)
from app.orchestrators.channels.inbox.process_comment_trigger_orchestrator import (
    ProcessCommentTriggerOrchestrator,
)
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.schemas.dto.channels.channel_settings import ChannelView
from app.schemas.dto.channels.comment_replies import SetInstagramCommentRepliesCommand
from app.schemas.dto.channels.meta_connection import (
    CompleteWhatsAppSignupCommand,
    ConnectMetaPageCommand,
    ListMetaPagesCommand,
    MetaConnectionStartView,
    MetaPageList,
    MetaSignInOptionsQuery,
    MetaSignInOptionsView,
    StartMetaConnectionCommand,
)
from app.schemas.dto.jobs import JobReport, QueuedJobInput


class MetaConnectionOperatorFactories:
    """
    One operator per endpoint of Meta's self-serve connection, each the
    generic role chain over one use case, and the worker's private reply to
    a comment (its own orchestrator: claim the inbox event, reply, finish or
    release it). Each runs in the storage scope of the business its input
    names.
    """

    def __init__(
        self,
        dependencies: MetaConnectionDependencies,
        use_cases: MetaConnectionUseCaseFactories,
    ) -> None:
        self._dependencies: MetaConnectionDependencies = dependencies
        self._use_cases: MetaConnectionUseCaseFactories = use_cases

    def sign_in_options(
        self,
    ) -> OperatorContract[MetaSignInOptionsQuery, MetaSignInOptionsView]:
        return business_scoped_operator(
            self._use_cases.get_meta_sign_in_options(),
            self._dependencies.storage_scope,
        )

    def start_meta_connection(
        self,
    ) -> OperatorContract[StartMetaConnectionCommand, MetaConnectionStartView]:
        return business_scoped_operator(
            self._use_cases.start_meta_connection(), self._dependencies.storage_scope
        )

    def complete_whatsapp_signup(
        self,
    ) -> OperatorContract[CompleteWhatsAppSignupCommand, ChannelView]:
        return business_scoped_operator(
            self._use_cases.complete_whatsapp_signup(),
            self._dependencies.storage_scope,
        )

    def list_meta_pages(self) -> OperatorContract[ListMetaPagesCommand, MetaPageList]:
        return business_scoped_operator(
            self._use_cases.list_meta_pages(), self._dependencies.storage_scope
        )

    def connect_meta_page(
        self,
    ) -> OperatorContract[ConnectMetaPageCommand, ChannelView]:
        return business_scoped_operator(
            self._use_cases.connect_meta_page(), self._dependencies.storage_scope
        )

    def set_comment_replies(
        self,
    ) -> OperatorContract[SetInstagramCommentRepliesCommand, ChannelView]:
        return business_scoped_operator(
            self._use_cases.set_comment_replies(), self._dependencies.storage_scope
        )

    def process_comment_trigger(self) -> OperatorContract[QueuedJobInput, JobReport]:
        """The `process_comment_trigger` job, in its event's business."""

        deps = self._dependencies
        orchestrator = ProcessCommentTriggerOrchestrator(
            claim_inbound_event=deps.claim_inbound_event,
            reply_to_comment=self._use_cases.reply_to_comment_trigger(),
            finish_inbound_event=deps.finish_inbound_event,
            release_inbound_event=deps.release_inbound_event,
        )
        return BusinessScopedPipelineOperator[QueuedJobInput, JobReport](
            pipeline=OrchestratorPipeline[QueuedJobInput, JobReport](
                orchestrator=orchestrator
            ),
            storage_scope=deps.storage_scope,
        )
