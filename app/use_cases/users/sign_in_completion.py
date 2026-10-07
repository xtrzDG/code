"""Opening the session at the end of a sign-in (one or two factors)."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.platform_admins import PlatformAdminRegistryContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserSessionRepoContract
from app.contracts.support_access import SignInNoticeFacilitatorContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.mfa import AuthLevel
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.users import UserDocument, UserSessionDocument
from app.schemas.dto.users import LoginSessionView, UserView
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.mfa.constrained_strings import RecoveryCode
from app.schemas.typings.users.booleans import IsNewUser
from app.schemas.typings.users.constrained_strings import SessionUserAgent
from app.schemas.typings.users.strings import AccessToken
from app.utilities.analytics.product_event_drafts import sign_in_events
from app.utilities.security.access_tokens import (
    generate_access_token,
    hash_access_token,
)
from app.utilities.security.session_expiry import is_session_over, opening_expiries


class SignInCompletion:
    """
    The last step of every sign-in: a new session with a random bearer token
    (returned once; only its SHA-256 hash is stored), how it was signed in
    and when, the device (browser and address) and its expiries (30 days at
    most and a week unused; a day and twelve hours for platform admins), an
    audited LOGIN with the client's address, the sign-in (or sign-up)
    product events, and a notice to the person when the device is new to
    their live sessions.
    """

    def __init__(
        self,
        user_session_repo: UserSessionRepoContract,
        audit_log_repo: AuditLogRepoContract,
        user_view_transformer: TransformerContract[UserDocument, UserView],
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
        product_events: RecordProductEventFacilitatorContract,
        platform_admins: PlatformAdminRegistryContract,
        sign_in_notices: SignInNoticeFacilitatorContract,
    ) -> None:
        self._platform_admins: PlatformAdminRegistryContract = platform_admins
        self._sign_in_notices: SignInNoticeFacilitatorContract = sign_in_notices
        self._user_session_repo: UserSessionRepoContract = user_session_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._user_view_transformer: TransformerContract[UserDocument, UserView] = (
            user_view_transformer
        )
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._product_events: RecordProductEventFacilitatorContract = product_events

    def open_session(
        self,
        user: UserDocument,
        auth_level: AuthLevel,
        is_new_user: IsNewUser,
        client_ip_address: ClientIpAddress | None,
        user_agent: SessionUserAgent | None = None,
        recovery_codes: list[RecoveryCode] | None = None,
    ) -> LoginSessionView:
        now: Microseconds = self._wall_clock.now_unix()
        access_token: AccessToken = generate_access_token()
        expires_at, idle_expires_at = opening_expiries(
            self._app_settings,
            is_admin=self._platform_admins.role_of(user) is not None,
            now=now,
        )
        others: list[UserSessionDocument] = [
            other
            for other in self._user_session_repo.list_by_user(user.id)
            if not is_session_over(other, now)
        ]
        session = UserSessionDocument(
            user_id=user.id,
            token_hash=hash_access_token(access_token),
            expires_at=expires_at,
            auth_level=auth_level,
            authenticated_at=now,
            user_agent=user_agent,
            created_ip=client_ip_address,
            last_seen_at=now,
            last_seen_ip=client_ip_address,
            idle_expires_at=idle_expires_at,
            created_at=now,
            updated_at=now,
        )
        self._user_session_repo.save(session)
        self._sign_in_notices.notice_new_device(user, session, others)
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                actor_id=user.id,
                action=AuditAction.LOGIN,
                entity=AuditEntityName("user"),
                entity_id=AuditEntityReference(str(user.id)),
                ip_address=client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        self._product_events.record(*sign_in_events(user, is_new_user))
        return LoginSessionView(
            access_token=access_token,
            expires_at=session.expires_at,
            user=self._user_view_transformer.transform(user),
            is_new_user=is_new_user,
            auth_level=auth_level,
            recovery_codes=list(recovery_codes or []),
        )
