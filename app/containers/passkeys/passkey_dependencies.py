from dataclasses import dataclass

from typed_time_provider import Microseconds, WallClock

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.passkeys import PasskeyCeremonyAdapterContract
from app.contracts.platform_admins import PlatformAdminRegistryContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.mfa_repositories import (
    MfaChallengeRepoContract,
    RecoveryCodeRepoContract,
    TotpFactorRepoContract,
)
from app.contracts.repositories.passkey_repositories import (
    PasskeyChallengeRepoContract,
    PasskeyRepoContract,
)
from app.contracts.repositories.user_repositories import (
    UserRepoContract,
    UserSessionRepoContract,
)
from app.contracts.session_assurance import (
    SessionAssuranceContract,
    StepUpGuardContract,
)
from app.contracts.storage import StorageScopeContract
from app.contracts.support_access import SignInNoticeFacilitatorContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.users import UserDocument
from app.schemas.dto.users import UserView


@dataclass(frozen=True, slots=True, kw_only=True)
class PasskeyDependencies:
    """
    Everything the passkey context (W20, migration 1201) takes from the rest
    of the application, as contracts: the person's repositories (platform
    collections), the WebAuthn ceremony, the session's assurance and the
    step-up guard, the sign-in's side effects and the settings it reads.
    The only place the dependency graph meets the typed root (the provider
    in app/containers/use_cases/passkey_root_provider.py fills it).
    """

    passkey_repo: PasskeyRepoContract
    challenge_repo: PasskeyChallengeRepoContract
    user_repo: UserRepoContract
    user_session_repo: UserSessionRepoContract
    mfa_challenge_repo: MfaChallengeRepoContract
    totp_factor_repo: TotpFactorRepoContract
    recovery_code_repo: RecoveryCodeRepoContract
    audit_log_repo: AuditLogRepoContract
    ceremony: PasskeyCeremonyAdapterContract
    session_assurance: SessionAssuranceContract
    step_up: StepUpGuardContract
    user_view_transformer: TransformerContract[UserDocument, UserView]
    rate_limit_registry: RequestRateLimitRegistryContract
    product_events: RecordProductEventFacilitatorContract
    platform_admins: PlatformAdminRegistryContract
    sign_in_notices: SignInNoticeFacilitatorContract
    storage_scope: StorageScopeContract
    app_settings: AppSettings
    wall_clock: WallClock[Microseconds]
