from app.contracts.repositories import BusinessRepoContract, ChannelRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.channels import WidgetMessageCommand
from app.schemas.dto.conversations import InboundMessage
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.channels.strings import WidgetContactNameInput
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.utilities.channels.delivery_targets import find_business_channel

MAX_CONTACT_NAME_LENGTH: int = 100


class AcceptWidgetMessageUseCase(UseCaseContract[WidgetMessageCommand, InboundMessage]):
    """
    Turn a website widget message into the engine's InboundMessage.

    The business must exist and have the widget switched on; otherwise the
    chat is reported as unavailable (the same answer for both, so business
    ids cannot be probed). The visitor is identified by the widget's random
    session key.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        channel_repo: ChannelRepoContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._channel_repo: ChannelRepoContract = channel_repo

    def run(self, input_data: WidgetMessageCommand) -> InboundMessage:
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
