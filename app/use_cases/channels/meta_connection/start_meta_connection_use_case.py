from typed_time_provider import Microseconds, WallClock

from app.contracts.meta_connection import MetaConnectionStateRepoContract
from app.contracts.repositories.business_closure_repositories import (
    BusinessClosureRepoContract,
)
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.meta_connection import (
    MetaConnectionPurpose,
    MetaConnectionRefusal,
)
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.meta_connections import MetaConnectionStateDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.channels.meta_connection import (
    MetaConnectionStartView,
    StartMetaConnectionCommand,
)
from app.schemas.dto.channels.meta_provider import MetaAppCredentials
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.meta_connection.constrained_strings import (
    MetaConfigurationId,
    MetaConnectionState,
)
from app.use_cases.channels.meta_connection.meta_states import (
    generate_state,
    hash_state,
    meta_refusal,
    state_end,
)
from app.use_cases.shared.closure_guard import refuse_while_closing
from app.utilities.channels.meta_sign_in import (
    META_GRAPH_API_VERSION,
    PAGE_PERMISSIONS,
    meta_app_of,
)

# Sign-ins a business keeps open at once; starting one more drops the oldest.
MAX_OPEN_SIGN_INS: int = 5


class StartMetaConnectionUseCase(
    UseCaseContract[StartMetaConnectionCommand, MetaConnectionStartView]
):
    """
    The owner presses "Continue with Facebook": a one-time state bound to
    the owner, the business and the purpose is stored (hashed) for fifteen
    minutes, and the cabinet gets what its Facebook SDK opens Meta's window
    with: the app, the Graph API version and the Embedded Signup
    configuration (WhatsApp) or the permissions to ask for (the page
    picker).

    The business's ended sign-ins are deleted here, and at most five stay
    open (the oldest goes), so abandoned ones neither pile up nor keep an
    owner's token for long. Without the platform's Meta app (or, for
    WhatsApp, its signup configuration) the start is refused as
    `meta_not_configured`.

    Starting is an owner's sensitive step (step-up): the session confirms
    it is its person here, before Meta's window opens, because the code
    Meta hands back lives about thirty seconds and must not wait for a
    confirmation when the signup completes. A closing business (a closure
    not cancelled) starts none: ConflictError.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        state_repo: MetaConnectionStateRepoContract,
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
        self._step_up: StepUpGuardContract = step_up
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: StartMetaConnectionCommand) -> MetaConnectionStartView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        refuse_while_closing(self._closure_repo, business.id, "connect a channel")
        self._step_up.require_recent_authentication()
        purpose: MetaConnectionPurpose = input_data.request.purpose
        app: MetaAppCredentials | None = meta_app_of(self._app_settings)
        configuration_id: MetaConfigurationId | None = (
            self._app_settings.meta_embedded_signup_config_id
        )
        if app is None or (
            purpose is MetaConnectionPurpose.WHATSAPP and configuration_id is None
        ):
            raise meta_refusal(
                MetaConnectionRefusal.NOT_CONFIGURED,
                "Facebook sign-in is not set up on this server: enter the "
                "details manually.",
            )

        now: Microseconds = self._wall_clock.now_unix()
        self._tidy(business.id, now)
        state: MetaConnectionState = generate_state()
        expires_at: Microseconds = state_end(now)
        self._state_repo.save(
            MetaConnectionStateDocument(
                business_id=business.id,
                user_id=input_data.user_id,
                purpose=purpose,
                state_hash=hash_state(state),
                expires_at=expires_at,
                created_at=now,
                updated_at=now,
            )
        )
        is_whatsapp: bool = purpose is MetaConnectionPurpose.WHATSAPP
        return MetaConnectionStartView(
            purpose=purpose,
            state=state,
            app_id=app.app_id,
            graph_api_version=META_GRAPH_API_VERSION,
            configuration_id=configuration_id if is_whatsapp else None,
            permissions=[] if is_whatsapp else list(PAGE_PERMISSIONS),
            expires_at=expires_at,
        )

    def _tidy(self, business_id: BusinessId, now: Microseconds) -> None:
        """Delete ended sign-ins, and the oldest beyond the open limit."""

        open_states: list[MetaConnectionStateDocument] = []
        for stored in self._state_repo.list_of_business(business_id):
            if int(stored.expires_at) <= int(now):
                self._state_repo.delete(business_id, stored.state_hash)
            else:
                open_states.append(stored)

        open_states.sort(key=lambda stored: int(stored.created_at))
        for stored in open_states[: max(0, len(open_states) - MAX_OPEN_SIGN_INS + 1)]:
            self._state_repo.delete(business_id, stored.state_hash)
