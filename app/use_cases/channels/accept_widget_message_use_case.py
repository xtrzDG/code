from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.business_repositories import (
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.channels.widget import WidgetMessageCommand
from app.schemas.dto.conversations import InboundMessage
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.channels.strings import WidgetContactNameInput
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.utilities.channels.delivery_targets import find_business_channel
from app.utilities.channels.widget_rate_limits import (
    WIDGET_MESSAGE_LIMITS,
    refuse_too_frequent_widget_requests,
)

MAX_CONTACT_NAME_LENGTH: int = 100


class AcceptWidgetMessageUseCase(UseCaseContract[WidgetMessageCommand, InboundMessage]):
    """
    Turn a website widget message into the engine's InboundMessage.

    The business must exist and have the widget switched on; otherwise the
    chat is reported as unavailable (the same answer for both, so business
    ids cannot be probed). Its assistant must be live (409 otherwise, as a
    turn would refuse it): the widget hears it at once instead of waiting
    for an answer that never comes. The visitor is identified by the
    widget's random session key.

    The endpoint is public and every message costs a model call, so
    messages are limited per visitor, per client network (an IPv6 /64), per
    business and for the platform before anything is read (429 with
    Retry-After, `WIDGET_MESSAGE_LIMITS`); the caller chooses the session
    key, so the other limits bound the model spend.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        channel_repo: ChannelRepoContract,
        rate_limit_registry: RequestRateLimitRegistryContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._rate_limit_registry: RequestRateLimitRegistryContract = (
            rate_limit_registry
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: WidgetMessageCommand) -> InboundMessage:
        refuse_too_frequent_widget_requests(
            self._rate_limit_registry,
            WIDGET_MESSAGE_LIMITS,
            business_id=input_data.business_id,
            session_key=input_data.request.session_key,
            client_ip_address=input_data.client_ip_address,
            now=self._wall_clock.now_unix(),
        )
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        channel: ChannelDocument | None = (
            None
            if business is None
            else find_business_channel(
                self._channel_repo,
                business.id,
                ChannelKind.WEB_CHAT,
            )
        )
        if (
            business is None
            or channel is None
            or channel.status is not ChannelStatus.CONNECTED
        ):
            raise NotFoundError("This chat is not available.")

        if business.status is not BusinessStatus.LIVE:
            raise ConflictError(f"The assistant of {business.name} is not live.")

        return InboundMessage(
            business_id=business.id,
            channel=ChannelKind.WEB_CHAT,
            channel_user_id=ChannelUserId(str(input_data.request.session_key)),
            text=MessageText(str(input_data.request.text)),
            contact_name=read_contact_name(input_data.request.contact_name),
        )


def read_contact_name(raw_name: WidgetContactNameInput | None) -> ContactName | None:
    """The visitor's name without surrounding spaces; blank means none."""

    if raw_name is None:
        return None

    name_text: str = raw_name.strip()
    if name_text == "":
        return None

    if len(name_text) > MAX_CONTACT_NAME_LENGTH:
        raise ValidationFailedError(
            f"contact_name must be at most {MAX_CONTACT_NAME_LENGTH} characters."
        )

    return ContactName(name_text)
