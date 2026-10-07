from typed_time_provider import Microseconds, WallClock

from app.contracts.channel_clients import TelegramBotApiClientContract
from app.contracts.media_clients import TelegramFileClientContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.channels.provider_profiles import TelegramBotProfile
from app.schemas.dto.channels.telegram_token_checks import (
    TelegramBotCheckView,
    ValidateTelegramTokenCommand,
)
from app.schemas.dto.errors import ErrorReason
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.exceptions.application_errors import (
    RateLimitedError,
    ValidationFailedError,
)
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import (
    ErrorReasonCode,
    RateLimitKey,
)
from app.schemas.typings.platform.strings import ErrorReasonMessage
from app.use_cases.channels.connection.telegram_avatar import fetch_bot_avatar
from app.use_cases.channels.connection.telegram_connection import read_bot_token

TOKEN_FORMAT_REASON: ErrorReasonCode = ErrorReasonCode("telegram_token_format")
TOKEN_REJECTED_REASON: ErrorReasonCode = ErrorReasonCode("telegram_token_rejected")
CHECK_WINDOW: RateWindowSeconds = RateWindowSeconds(10 * 60)
# An owner pastes a token a few times at most; twenty checks in ten minutes
# leave room for typos and stop a business from probing tokens in bulk.
CHECKS_PER_WINDOW: RequestsPerWindow = RequestsPerWindow(20)


class ValidateTelegramTokenUseCase(
    UseCaseContract[ValidateTelegramTokenCommand, TelegramBotCheckView]
):
    """
    Which bot a pasted @BotFather token opens, before anything is saved: the
    guided Telegram connection shows its name and photo so the owner sees
    the right bot ("Mtsvane Ezo, @mtsvane_ezo_bot") and only then connects
    it. Telegram's getMe answers; the photo comes from getUserProfilePhotos
    and is inlined (its address holds the token). Nothing is stored and no
    webhook is set.

    Owners only, 20 checks per business in 10 minutes (429 after that). A
    token of the wrong shape is refused with reason `telegram_token_format`,
    one Telegram does not accept with `telegram_token_rejected` (both 422);
    Telegram being unreachable is a 502.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        telegram_client: TelegramBotApiClientContract,
        telegram_file_client: TelegramFileClientContract,
        rate_limit_registry: RequestRateLimitRegistryContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._telegram_client: TelegramBotApiClientContract = telegram_client
        self._telegram_file_client: TelegramFileClientContract = telegram_file_client
        self._rate_limit_registry: RequestRateLimitRegistryContract = (
            rate_limit_registry
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ValidateTelegramTokenCommand) -> TelegramBotCheckView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        self._count_check(business)
        bot_token: ChannelSecret = read_checked_token(input_data)
        try:
            profile: TelegramBotProfile = self._telegram_client.get_me(bot_token)
        except ValidationFailedError as error:
            raise ValidationFailedError(
                str(error), reasons=[token_reason(TOKEN_REJECTED_REASON, error)]
            ) from None

        return TelegramBotCheckView(
            username=profile.username,
            display_name=profile.display_name,
            avatar_data_url=fetch_bot_avatar(
                self._telegram_client,
                self._telegram_file_client,
                bot_token,
                profile,
            ),
        )

    def _count_check(self, business: BusinessDocument) -> None:
        now: Microseconds = self._wall_clock.now_unix()
        counter = RateLimitCounter(
            key=RateLimitKey(f"telegram-token-check:business:{business.id}"),
            limit=CHECKS_PER_WINDOW,
        )
        if self._rate_limit_registry.try_acquire_all([counter], CHECK_WINDOW, now):
            raise RateLimitedError(
                "Too many token checks. Try again in a few minutes.",
                retry_after_seconds=self._rate_limit_registry.seconds_until_free(
                    counter, CHECK_WINDOW, now
                ),
            )


def read_checked_token(input_data: ValidateTelegramTokenCommand) -> ChannelSecret:
    """The token, or 422 with reason `telegram_token_format`."""

    try:
        return read_bot_token(input_data.request.bot_token)
    except ValidationFailedError as error:
        raise ValidationFailedError(
            str(error), reasons=[token_reason(TOKEN_FORMAT_REASON, error)]
        ) from None


def token_reason(code: ErrorReasonCode, error: ValidationFailedError) -> ErrorReason:
    return ErrorReason(code=code, message=ErrorReasonMessage(str(error)))
