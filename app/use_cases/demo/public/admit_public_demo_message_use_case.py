from typed_time_provider import Microseconds, WallClock

from app.contracts.public_demos import PublicDemoDirectoryRegistryContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.conversations import InboundMessage
from app.schemas.dto.public_demo import PublicDemoMessageCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.utilities.public_site.public_demo_limits import (
    refuse_too_many_demo_messages,
)

DEMO_CHANNEL_USER_PREFIX: str = "public-demo"


class AdmitPublicDemoMessageUseCase(
    UseCaseContract[PublicDemoMessageCommand, InboundMessage]
):
    """
    Turn a landing-page visitor's message into a sandbox customer message
    of a demo business: only a business on the demo list (else 404, so the
    route reveals no other business), only with a published assistant, and
    within the demo limits (`public_demo_limits`, else 429). The message
    goes to the OWNER_TEST channel under the visitor's conversation key and
    is a sandbox turn: bookings and requests are test records, no staff is
    alerted, nothing is billed and the inbox does not show it.

    Raises:
        NotFoundError: not a demo business, or it has no published assistant.
        RateLimitedError: a demo limit is used up (Retry-After).
    """

    def __init__(
        self,
        public_demo_directory: PublicDemoDirectoryRegistryContract,
        business_repo: BusinessRepoContract,
        rate_limit_registry: RequestRateLimitRegistryContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._directory: PublicDemoDirectoryRegistryContract = public_demo_directory
        self._business_repo: BusinessRepoContract = business_repo
        self._rate_limit_registry: RequestRateLimitRegistryContract = (
            rate_limit_registry
        )
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PublicDemoMessageCommand) -> InboundMessage:
        business: BusinessDocument | None = (
            self._business_repo.get(input_data.business_id)
            if self._directory.includes(input_data.business_id)
            else None
        )
        if business is None or business.published_assistant_version_id is None:
            raise NotFoundError("This demo is not available.")

        refuse_too_many_demo_messages(
            self._rate_limit_registry,
            business.id,
            input_data.request.session_key,
            input_data.client_ip_address,
            self._app_settings.public_site.demo_messages_per_hour,
            self._wall_clock.now_unix(),
        )
        return InboundMessage(
            business_id=business.id,
            channel=ChannelKind.OWNER_TEST,
            channel_user_id=ChannelUserId(
                f"{DEMO_CHANNEL_USER_PREFIX}:{input_data.request.session_key}"
            ),
            text=MessageText(str(input_data.request.text).strip()),
            is_sandbox=True,
            assistant_version_id=business.published_assistant_version_id,
        )
