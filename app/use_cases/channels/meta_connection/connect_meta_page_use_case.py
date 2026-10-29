from typed_time_provider import Microseconds, WallClock

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.channel_clients import MetaGraphApiClientContract
from app.contracts.meta_connection import (
    MetaConnectionStateRepoContract,
    MetaOAuthClientContract,
    MetaPagesClientContract,
)
from app.contracts.repositories.business_closure_repositories import (
    BusinessClosureRepoContract,
)
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.storage import StorageScopeContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.meta_connection import (
    MetaConnectionPurpose,
    MetaConnectionRefusal,
)
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument, ChannelPublicProfile
from app.schemas.domain.meta_connections import MetaConnectionStateDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.channels.channel_settings import ChannelView
from app.schemas.dto.channels.meta_connection import ConnectMetaPageCommand
from app.schemas.dto.channels.meta_provider import MetaAppCredentials
from app.schemas.dto.channels.provider_profiles import MetaPageProfile
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.channels.constrained_strings import MetaObjectId
from app.schemas.typings.channels.strings import ChannelExternalId, ChannelSecret
from app.schemas.typings.meta_connection.constrained_strings import (
    MetaConnectionStateHash,
)
from app.schemas.typings.meta_connection.strings import (
    MetaAccessToken,
    MetaPageAccessToken,
)
from app.use_cases.channels.channel_views import build_channel_view
from app.use_cases.channels.connection.channel_connection import ChannelConnection
from app.use_cases.channels.meta_connection.meta_channel_writes import (
    MetaChannelStores,
    require_free_account,
    save_connected_channel,
)
from app.use_cases.channels.meta_connection.meta_states import (
    hash_state,
    is_open_for,
    link_expired,
    meta_refusal,
)
from app.use_cases.shared.closure_guard import refuse_while_closing
from app.utilities.channels.meta_sign_in import meta_app_of

PAGE_CHANNELS: frozenset[ChannelKind] = frozenset(
    {ChannelKind.MESSENGER, ChannelKind.INSTAGRAM}
)


class ConnectMetaPageUseCase(UseCaseContract[ConnectMetaPageCommand, ChannelView]):
    """
    The owner picked a page: Messenger (any page they manage) or Instagram
    (the professional account linked to the page) is connected with it.

    The page-picker sign-in that listed the pages must be this owner's, in
    this business, still open, with its token kept. That token is traded
    for a long-lived one, which reads the page's own token (one that does
    not expire). The page is then checked and subscribed as a pasted token
    is (the page and its Instagram account; an account another business
    connected is refused; the app is subscribed to the page's messages),
    and the channel stores the page token encrypted and the public
    usernames customers open a chat with. The sign-in ends with the
    connection (its token is deleted). A closing business (a closure not
    cancelled) connects nothing: ConflictError, before Meta is asked.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        state_repo: MetaConnectionStateRepoContract,
        oauth_client: MetaOAuthClientContract,
        pages_client: MetaPagesClientContract,
        meta_client: MetaGraphApiClientContract,
        channel_repo: ChannelRepoContract,
        secret_cipher: SecretCipherAdapterContract,
        audit_log_repo: AuditLogRepoContract,
        product_events: RecordProductEventFacilitatorContract,
        storage_scope: StorageScopeContract,
        step_up: StepUpGuardContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
        closure_repo: BusinessClosureRepoContract | None = None,
    ) -> None:
        self._closure_repo: BusinessClosureRepoContract | None = closure_repo
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._state_repo: MetaConnectionStateRepoContract = state_repo
        self._oauth_client: MetaOAuthClientContract = oauth_client
        self._pages_client: MetaPagesClientContract = pages_client
        self._meta_client: MetaGraphApiClientContract = meta_client
        self._stores = MetaChannelStores(
            channel_repo=channel_repo,
            secret_cipher=secret_cipher,
            audit_log_repo=audit_log_repo,
            product_events=product_events,
            storage_scope=storage_scope,
        )
        self._step_up: StepUpGuardContract = step_up
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ConnectMetaPageCommand) -> ChannelView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        if input_data.channel not in PAGE_CHANNELS:
            raise NotFoundError("Only Messenger and Instagram connect a page.")

        refuse_while_closing(self._closure_repo, business.id, "connect a channel")
        self._step_up.require_recent_authentication()
        app: MetaAppCredentials | None = meta_app_of(self._app_settings)
        if app is None:
            raise meta_refusal(
                MetaConnectionRefusal.NOT_CONFIGURED,
                "Facebook sign-in is not set up on this server.",
            )

        now: Microseconds = self._wall_clock.now_unix()
        state_hash: MetaConnectionStateHash = hash_state(input_data.request.state)
        user_token: MetaAccessToken = self._kept_token(
            self._state_repo.get(business.id, state_hash), input_data, now
        )
        page_token: MetaPageAccessToken | None = self._pages_client.read_page_token(
            self._oauth_client.extend_user_token(user_token, app),
            input_data.request.page_id,
            app,
        )
        if page_token is None:
            raise meta_refusal(
                MetaConnectionRefusal.PAGE_NOT_FOUND,
                "This page is not among the pages you manage on Facebook.",
            )

        connection: ChannelConnection = self._connect(business, input_data, page_token)
        channel: ChannelDocument = save_connected_channel(
            self._stores,
            business.id,
            input_data.user_id,
            input_data.channel,
            connection,
            now,
            input_data.client_ip_address,
        )
        self._state_repo.delete(business.id, state_hash)
        return build_channel_view(channel)

    def _kept_token(
        self,
        state: MetaConnectionStateDocument | None,
        input_data: ConnectMetaPageCommand,
        now: Microseconds,
    ) -> MetaAccessToken:
        if (
            state is None
            or state.encrypted_user_token is None
            or not is_open_for(
                state, input_data.user_id, MetaConnectionPurpose.PAGES, now
            )
        ):
            raise link_expired()

        try:
            return MetaAccessToken(
                str(self._stores.secret_cipher.decrypt(state.encrypted_user_token))
            )
        except ValidationFailedError:
            raise link_expired() from None

    def _connect(
        self,
        business: BusinessDocument,
        input_data: ConnectMetaPageCommand,
        page_token: MetaPageAccessToken,
    ) -> ChannelConnection:
        """
        The page (and its Instagram account) as Meta tells it; the account
        must be free; the app is subscribed to the page's messages.
        """

        credential = ChannelSecret(str(page_token))
        profile: MetaPageProfile = self._meta_client.get_page(
            credential, input_data.request.page_id
        )
        account_id: MetaObjectId = profile.page_id
        if input_data.channel is ChannelKind.INSTAGRAM:
            if profile.instagram_account_id is None:
                raise meta_refusal(
                    MetaConnectionRefusal.NO_INSTAGRAM_ACCOUNT,
                    "No Instagram professional account is linked to this page.",
                )

            account_id = profile.instagram_account_id

        external_id = ChannelExternalId(str(account_id))
        require_free_account(self._stores, business.id, input_data.channel, external_id)
        self._meta_client.subscribe_page(credential, profile.page_id)
        return ChannelConnection(
            external_id=external_id,
            secret=credential,
            public_profile=ChannelPublicProfile(
                page_username=profile.username,
                instagram_username=(
                    profile.instagram_username
                    if input_data.channel is ChannelKind.INSTAGRAM
                    else None
                ),
            ),
        )
