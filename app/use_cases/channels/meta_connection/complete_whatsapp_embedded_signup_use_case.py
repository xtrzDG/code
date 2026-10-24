from typed_time_provider import Microseconds, WallClock

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.meta_connection import (
    MetaConnectionStateRepoContract,
    MetaOAuthClientContract,
    WhatsAppOnboardingClientContract,
)
from app.contracts.repositories.business_closure_repositories import (
    BusinessClosureRepoContract,
)
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
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
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.channels.channel_settings import ChannelView
from app.schemas.dto.channels.meta_connection import (
    CompleteWhatsAppSignupCommand,
    CompleteWhatsAppSignupRequest,
)
from app.schemas.dto.channels.meta_provider import MetaAppCredentials
from app.schemas.dto.channels.provider_profiles import WhatsAppPhoneNumberProfile
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.exceptions.meta_connection_errors import WhatsAppPinMismatchError
from app.schemas.typings.channels.strings import ChannelExternalId, ChannelSecret
from app.schemas.typings.meta_connection.constrained_strings import (
    WhatsAppBusinessAccountId,
    WhatsAppRegistrationPin,
)
from app.schemas.typings.meta_connection.strings import MetaAccessToken
from app.use_cases.channels.channel_views import build_channel_view
from app.use_cases.channels.connection.channel_connection import ChannelConnection
from app.use_cases.channels.connection.meta_connections import read_whatsapp_number
from app.use_cases.channels.meta_connection.meta_channel_writes import (
    MetaChannelStores,
    require_free_account,
    save_connected_channel,
)
from app.use_cases.channels.meta_connection.meta_states import (
    meta_refusal,
    take_state,
)
from app.use_cases.channels.meta_connection.whatsapp_registration_pins import (
    keeping_pin,
    registration_pin,
)
from app.use_cases.channels.meta_connection.whatsapp_signup_steps import (
    choose_business_account,
    choose_phone_number,
)
from app.use_cases.shared.closure_guard import refuse_while_closing
from app.utilities.channels.delivery_targets import find_business_channel
from app.utilities.channels.meta_sign_in import meta_app_of


class CompleteWhatsAppEmbeddedSignupUseCase(
    UseCaseContract[CompleteWhatsAppSignupCommand, ChannelView]
):
    """
    The owner finished WhatsApp Embedded Signup in Meta's window: the
    business's number is connected without a single pasted id.

    1. The sign-in's state must be one this owner started for WhatsApp in
       this business, open and unused; it is used up before anything else.
    2. Meta's code becomes the business's own token (`MetaOAuthClient`).
    3. `debug_token`'s granular permissions name the WhatsApp Business
       Account (the one Meta's window reported, when it is among them),
       and the account's numbers the number (likewise).
    4. The platform's app is subscribed to the account's webhooks and the
       number registered for the Cloud API with a two-step PIN (the one
       this channel registered the number with before, even while it was
       off, else a new random one).
    5. The channel stores the account, the token and the PIN encrypted, and
       the number as customers see it, so share links and the hosted page
       get their WhatsApp button; the audit log and the product events note
       the connection.

    No second step-up: the state was made only after the owner confirmed
    their identity (`StartMetaConnectionUseCase`) and is bound to them,
    this business and WhatsApp, so it carries that proof. Asking again here
    would let Meta's short-lived, single-use code run out while the owner
    types a code, and the retry would find the state used. A number already
    connected to another business is refused; a number registered with
    another PIN is refused as `whatsapp_pin_mismatch` (its owner turns
    two-step verification off in WhatsApp Manager, then starts again). A
    closing business (a closure not cancelled) connects nothing:
    ConflictError, before the state is used or Meta is asked.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        state_repo: MetaConnectionStateRepoContract,
        oauth_client: MetaOAuthClientContract,
        onboarding_client: WhatsAppOnboardingClientContract,
        channel_repo: ChannelRepoContract,
        secret_cipher: SecretCipherAdapterContract,
        audit_log_repo: AuditLogRepoContract,
        product_events: RecordProductEventFacilitatorContract,
        storage_scope: StorageScopeContract,
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
        self._onboarding_client: WhatsAppOnboardingClientContract = onboarding_client
        self._stores = MetaChannelStores(
            channel_repo=channel_repo,
            secret_cipher=secret_cipher,
            audit_log_repo=audit_log_repo,
            product_events=product_events,
            storage_scope=storage_scope,
        )
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CompleteWhatsAppSignupCommand) -> ChannelView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        refuse_while_closing(self._closure_repo, business.id, "connect a channel")
        app: MetaAppCredentials = self._require_app()
        request: CompleteWhatsAppSignupRequest = input_data.request
        now: Microseconds = self._wall_clock.now_unix()
        take_state(
            self._state_repo,
            business.id,
            input_data.user_id,
            request.state,
            MetaConnectionPurpose.WHATSAPP,
            now,
        )
        token: MetaAccessToken = self._oauth_client.exchange_code(request.code, app)
        account_id: WhatsAppBusinessAccountId = choose_business_account(
            self._oauth_client.read_grants(token, app),
            request.whatsapp_business_account_id,
        )
        number: WhatsAppPhoneNumberProfile = choose_phone_number(
            self._onboarding_client.list_phone_numbers(token, account_id, app),
            request.phone_number_id,
        )
        external_id = ChannelExternalId(str(number.phone_number_id))
        require_free_account(
            self._stores, business.id, ChannelKind.WHATSAPP, external_id
        )
        existing: ChannelDocument | None = find_business_channel(
            self._stores.channel_repo, business.id, ChannelKind.WHATSAPP
        )
        pin: WhatsAppRegistrationPin = registration_pin(
            existing, external_id, self._stores.secret_cipher
        )
        self._onboarding_client.subscribe_app(token, account_id, app)
        self._register(token, number, pin, app)

        def keep_signup(channel: ChannelDocument) -> None:
            channel.whatsapp_business_account_id = account_id
            channel.whatsapp_registration_pins = keeping_pin(
                channel.whatsapp_registration_pins,
                external_id,
                self._stores.secret_cipher.encrypt(ChannelSecret(str(pin))),
            )

        channel: ChannelDocument = save_connected_channel(
            self._stores,
            business.id,
            input_data.user_id,
            ChannelKind.WHATSAPP,
            ChannelConnection(
                external_id=external_id,
                secret=ChannelSecret(str(token)),
                public_profile=ChannelPublicProfile(
                    whatsapp_number=read_whatsapp_number(number.display_phone_number)
                ),
            ),
            now,
            input_data.client_ip_address,
            complete=keep_signup,
        )
        return build_channel_view(channel)

    def _require_app(self) -> MetaAppCredentials:
        app: MetaAppCredentials | None = meta_app_of(self._app_settings)
        if app is None or self._app_settings.meta_embedded_signup_config_id is None:
            raise meta_refusal(
                MetaConnectionRefusal.NOT_CONFIGURED,
                "WhatsApp Embedded Signup is not set up on this server.",
            )

        return app

    def _register(
        self,
        token: MetaAccessToken,
        number: WhatsAppPhoneNumberProfile,
        pin: WhatsAppRegistrationPin,
        app: MetaAppCredentials,
    ) -> None:
        try:
            self._onboarding_client.register_number(
                token, number.phone_number_id, pin, app
            )
        except WhatsAppPinMismatchError:
            raise meta_refusal(
                MetaConnectionRefusal.WHATSAPP_PIN_MISMATCH,
                "This WhatsApp number has its own two-step verification PIN. "
                "Turn two-step verification off in WhatsApp Manager and start "
                "again.",
                error_type=ConflictError,
            ) from None
