from app.containers.meta_connection.meta_connection_dependencies import (
    MetaConnectionDependencies,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.channels.channel_settings import ChannelView
from app.schemas.dto.channels.channel_webhooks import MetaWebhookRequest
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
from app.schemas.dto.deliveries import InboundAnswer, InboundEventClaim, InboxIntake
from app.use_cases.channels.comment_replies import (
    accept_instagram_comments_use_case as accept_comments,
)
from app.use_cases.channels.comment_replies import (
    reply_to_comment_trigger_use_case as reply_to_comment,
)
from app.use_cases.channels.comment_replies import (
    set_instagram_comment_replies_use_case as set_comment_replies,
)
from app.use_cases.channels.meta_connection import (
    complete_whatsapp_embedded_signup_use_case as complete_signup,
)
from app.use_cases.channels.meta_connection import (
    connect_meta_page_use_case as connect_page,
)
from app.use_cases.channels.meta_connection import (
    get_meta_sign_in_options_use_case as sign_in_options,
)
from app.use_cases.channels.meta_connection import (
    list_meta_pages_use_case as list_pages,
)
from app.use_cases.channels.meta_connection import (
    start_meta_connection_use_case as start_connection,
)


class MetaConnectionUseCaseFactories:
    """
    One typed factory per use case of Meta's self-serve connection: the
    Facebook sign-ins of the Channels page (WhatsApp Embedded Signup, the
    page picker of Messenger and Instagram) and Instagram comment-to-DM (its
    settings, the comments webhook's intake and the worker's private reply).
    Each call builds a fresh, stateless use case.
    """

    def __init__(self, dependencies: MetaConnectionDependencies) -> None:
        self._dependencies: MetaConnectionDependencies = dependencies

    def get_meta_sign_in_options(
        self,
    ) -> UseCaseContract[MetaSignInOptionsQuery, MetaSignInOptionsView]:
        deps = self._dependencies
        return sign_in_options.GetMetaSignInOptionsUseCase(
            authorize_business_access=deps.authorize_business_access,
            app_settings=deps.app_settings,
        )

    def start_meta_connection(
        self,
    ) -> UseCaseContract[StartMetaConnectionCommand, MetaConnectionStartView]:
        deps = self._dependencies
        return start_connection.StartMetaConnectionUseCase(
            authorize_business_access=deps.authorize_business_access,
            state_repo=deps.state_repo,
            step_up=deps.step_up,
            app_settings=deps.app_settings,
            wall_clock=deps.wall_clock,
            closure_repo=deps.closure_repo,
        )

    def complete_whatsapp_signup(
        self,
    ) -> UseCaseContract[CompleteWhatsAppSignupCommand, ChannelView]:
        deps = self._dependencies
        return complete_signup.CompleteWhatsAppEmbeddedSignupUseCase(
            authorize_business_access=deps.authorize_business_access,
            state_repo=deps.state_repo,
            oauth_client=deps.oauth_client,
            onboarding_client=deps.onboarding_client,
            channel_repo=deps.channel_repo,
            secret_cipher=deps.secret_cipher,
            audit_log_repo=deps.audit_log_repo,
            product_events=deps.product_events,
            storage_scope=deps.storage_scope,
            app_settings=deps.app_settings,
            wall_clock=deps.wall_clock,
            closure_repo=deps.closure_repo,
        )

    def list_meta_pages(self) -> UseCaseContract[ListMetaPagesCommand, MetaPageList]:
        deps = self._dependencies
        return list_pages.ListMetaPagesUseCase(
            authorize_business_access=deps.authorize_business_access,
            state_repo=deps.state_repo,
            oauth_client=deps.oauth_client,
            pages_client=deps.pages_client,
            secret_cipher=deps.secret_cipher,
            app_settings=deps.app_settings,
            wall_clock=deps.wall_clock,
        )

    def connect_meta_page(self) -> UseCaseContract[ConnectMetaPageCommand, ChannelView]:
        deps = self._dependencies
        return connect_page.ConnectMetaPageUseCase(
            authorize_business_access=deps.authorize_business_access,
            state_repo=deps.state_repo,
            oauth_client=deps.oauth_client,
            pages_client=deps.pages_client,
            meta_client=deps.meta_client,
            channel_repo=deps.channel_repo,
            secret_cipher=deps.secret_cipher,
            audit_log_repo=deps.audit_log_repo,
            product_events=deps.product_events,
            storage_scope=deps.storage_scope,
            step_up=deps.step_up,
            app_settings=deps.app_settings,
            wall_clock=deps.wall_clock,
            closure_repo=deps.closure_repo,
        )

    def set_comment_replies(
        self,
    ) -> UseCaseContract[SetInstagramCommentRepliesCommand, ChannelView]:
        deps = self._dependencies
        return set_comment_replies.SetInstagramCommentRepliesUseCase(
            authorize_business_access=deps.authorize_business_access,
            channel_repo=deps.channel_repo,
            audit_log_repo=deps.audit_log_repo,
            wall_clock=deps.wall_clock,
        )

    def accept_instagram_comments(
        self,
    ) -> UseCaseContract[MetaWebhookRequest, InboxIntake]:
        deps = self._dependencies
        return accept_comments.AcceptInstagramCommentsUseCase(
            channel_repo=deps.channel_repo,
            instagram_adapter=deps.instagram_adapter,
            inbound_event_repo=deps.inbound_event_repo,
            job_queue=deps.job_queue,
            wall_clock=deps.wall_clock,
            unit_of_work=deps.unit_of_work,
        )

    def reply_to_comment_trigger(
        self,
    ) -> UseCaseContract[InboundEventClaim, InboundAnswer]:
        deps = self._dependencies
        return reply_to_comment.ReplyToCommentTriggerUseCase(
            channel_repo=deps.channel_repo,
            contact_repo=deps.contact_repo,
            suppression_list=deps.suppression_list,
            outbound_message_repo=deps.outbound_message_repo,
            job_queue=deps.job_queue,
            rate_limit_registry=deps.rate_limit_registry,
            wall_clock=deps.wall_clock,
            unit_of_work=deps.unit_of_work,
        )
