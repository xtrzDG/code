"""Send a login code to a checked destination, within the abuse limits."""

from typed_time_provider import Microseconds, Seconds, WallClock

from app.contracts.facilitators import OtpDeliveryFacilitatorContract
from app.contracts.login_protection import (
    BotCheckFacilitatorContract,
    LoginCodeCapAlertFacilitatorContract,
)
from app.contracts.registries import LoginCodeSendLockRegistryContract
from app.contracts.repositories.user_repositories import OtpChallengeRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.domain.users import OtpChallengeDocument
from app.schemas.dto.login_protection import LoginCodeDestination, SendLoginCodeCommand
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.login_errors import LoginCodeCapReachedError
from app.schemas.typings.users.constrained_strings import OtpCode
from app.schemas.typings.users.prefixed_id import OtpChallengeId
from app.use_cases.users.otp_login.login_code_delivery import deliver_login_code
from app.use_cases.users.otp_login.login_code_limits import (
    LIMIT_WINDOW_SECONDS,
    refuse_over_login_code_limits,
)
from app.use_cases.users.otp_login.login_risk_signals import (
    require_bot_check_when_risky,
)
from app.utilities.security.one_time_codes import generate_otp_code, hash_otp_code


class SendLoginCodeUseCase(UseCaseContract[SendLoginCodeCommand, OtpChallengeDocument]):
    """
    Send a new login code and store its challenge (only a keyed hash of the
    code).

    Every code is a paid message, so a send is guarded against abuse (SMS
    pumping, login floods):
    - a risky request (a phone or e-mail of no verified user, a busy client
      address, half the platform budget used, a high-risk country) needs a
      passed bot check (Cloudflare Turnstile) when the check is on;
    - a second request for the same destination and channel within 30
      seconds is refused (one immediate switch to another channel is
      allowed, for a number that is not on WhatsApp), and so is a send over
      the hourly caps per destination, per client address, per country (new
      phones) and in total, where verified users have a budget of their own;
      the platform team is alerted when a platform cap refuses sends.
    The check of the caps and the reservation of the send happen under one
    lock, before any provider is called, so parallel requests cannot all
    pass; a failed delivery drops its reservation. When a provider fails,
    the next channel carries the same code; when every one fails, the
    details are logged and the caller gets a generic message.
    """

    def __init__(
        self,
        otp_challenge_repo: OtpChallengeRepoContract,
        otp_delivery_facilitator: OtpDeliveryFacilitatorContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
        send_lock_registry: LoginCodeSendLockRegistryContract,
        bot_check: BotCheckFacilitatorContract,
        cap_alerts: LoginCodeCapAlertFacilitatorContract,
    ) -> None:
        self._otp_challenge_repo: OtpChallengeRepoContract = otp_challenge_repo
        self._otp_delivery_facilitator: OtpDeliveryFacilitatorContract = (
            otp_delivery_facilitator
        )
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._send_lock_registry: LoginCodeSendLockRegistryContract = send_lock_registry
        self._bot_check: BotCheckFacilitatorContract = bot_check
        self._cap_alerts: LoginCodeCapAlertFacilitatorContract = cap_alerts

    def run(self, input_data: SendLoginCodeCommand) -> OtpChallengeDocument:
        destination: LoginCodeDestination = input_data.destination
        # The bot check calls Cloudflare: before the lock, on a first read.
        require_bot_check_when_risky(
            self._bot_check,
            self._list_recent_challenges(),
            destination,
            input_data.turnstile_token,
            self._app_settings,
        )
        now: Microseconds = self._wall_clock.now_unix()
        challenge_id: OtpChallengeId = OtpChallengeId()
        code: OtpCode = generate_otp_code()
        challenge = OtpChallengeDocument(
            id=challenge_id,
            login_method=destination.login_method,
            phone_number=destination.phone_number,
            email=destination.email,
            country_code=destination.country_code,
            delivery_channel=input_data.delivery_channels[0],
            locale=input_data.locale,
            code_hash=hash_otp_code(challenge_id, code),
            expires_at=self._wall_clock.now_unix_with_delta(
                Seconds(int(self._app_settings.otp_lifetime_seconds))
            ),
            requested_from_ip=destination.client_ip_address,
            is_verified_destination=destination.is_verified_destination,
            created_at=now,
            updated_at=now,
        )
        self._reserve_send(challenge, destination)
        try:
            delivery_channel: OtpDeliveryChannel = deliver_login_code(
                self._otp_delivery_facilitator,
                delivery_channels=input_data.delivery_channels,
                phone_number=destination.phone_number,
                email=destination.email,
                code=code,
                locale=input_data.locale,
            )
        except ExternalServiceError:
            # A failed delivery leaves nothing to throttle.
            self._otp_challenge_repo.delete(challenge_id)
            raise

        if delivery_channel is not challenge.delivery_channel:
            challenge = challenge.model_copy(
                update={"delivery_channel": delivery_channel}
            )
            self._otp_challenge_repo.save(challenge)

        return challenge

    def _reserve_send(
        self,
        challenge: OtpChallengeDocument,
        destination: LoginCodeDestination,
    ) -> None:
        """Check the limits and reserve the send together, before any provider."""

        try:
            with self._send_lock_registry.lock():
                refuse_over_login_code_limits(
                    self._list_recent_challenges(),
                    destination,
                    self._wall_clock,
                    self._app_settings,
                )
                self._otp_challenge_repo.save(challenge)
        except LoginCodeCapReachedError as error:
            # Outside the lock: the alert may send e-mails.
            self._cap_alerts.report_cap_reached(error.alert)
            raise

    def _list_recent_challenges(self) -> list[OtpChallengeDocument]:
        return self._otp_challenge_repo.list_created_since(
            self._wall_clock.now_unix_with_delta(Seconds(-LIMIT_WINDOW_SECONDS))
        )
