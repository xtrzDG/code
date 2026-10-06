from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.contracts.widget_streams import WidgetStreamTicketSignerContract
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.channels.widget_streams import (
    WidgetStreamClaims,
    WidgetStreamGrant,
    WidgetStreamRequest,
)
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    NotFoundError,
)
from app.utilities.channels.delivery_targets import find_business_channel

TICKET_REFUSED: str = (
    "The stream ticket is not valid for this chat or has expired; the "
    "widget's next answer brings a new one."
)


class OpenWidgetStreamUseCase(UseCaseContract[WidgetStreamRequest, WidgetStreamGrant]):
    """
    Let a website visitor's widget open its live stream: the ticket must be
    one this platform signed for this business and not expired (401
    otherwise: the widget polls and gets a fresh ticket), and the chat must
    be switched on (404 like the other widget routes). The stream then
    hears this visitor only.
    """

    def __init__(
        self,
        ticket_signer: WidgetStreamTicketSignerContract,
        channel_repo: ChannelRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._ticket_signer: WidgetStreamTicketSignerContract = ticket_signer
        self._channel_repo: ChannelRepoContract = channel_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: WidgetStreamRequest) -> WidgetStreamGrant:
        claims: WidgetStreamClaims | None = self._ticket_signer.read(input_data.ticket)
        if (
            claims is None
            or claims.business_id != input_data.business_id
            or int(claims.expires_at) <= int(self._wall_clock.now_unix())
        ):
            raise AuthenticationRequiredError(TICKET_REFUSED)

        channel: ChannelDocument | None = find_business_channel(
            self._channel_repo, input_data.business_id, ChannelKind.WEB_CHAT
        )
        if channel is None or channel.status is not ChannelStatus.CONNECTED:
            raise NotFoundError("This chat is not available.")

        return WidgetStreamGrant(
            business_id=claims.business_id, visitor_id=claims.visitor_id
        )
