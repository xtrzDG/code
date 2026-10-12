from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.business_repositories import (
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.repositories.media_repositories import WidgetUploadRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.widget_uploads import WidgetUploadDocument
from app.schemas.dto.channels.widget import WidgetMessageCommand
from app.schemas.dto.channels.widget_uploads import AcceptedWidgetMessage
from app.schemas.dto.conversations import InboundMessage
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.channels.strings import WidgetContactNameInput
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.use_cases.channels.uploads.message_uploads import (
    inbound_attachment_of,
    read_message_uploads,
)
from app.use_cases.shared.widget_chats import (
    find_open_widget_chat,
    require_live_assistant,
)
from app.utilities.channels.channel_activity import stamp_channel_activity
from app.utilities.channels.widget_rate_limits import (
    WIDGET_MESSAGE_LIMITS,
    refuse_too_frequent_widget_requests,
)
from app.utilities.sharing.acquisition_sources import normalize_source

MAX_CONTACT_NAME_LENGTH: int = 100


class AcceptWidgetMessageUseCase(
    UseCaseContract[WidgetMessageCommand, AcceptedWidgetMessage]
):
    """
    Turn a website widget message into the engine's InboundMessage, with
    the photos and voice notes it names.

    The business must exist and have the widget switched on; otherwise the
    chat is reported as unavailable (the same answer for both, so business
    ids cannot be probed). Its assistant must be live (409 otherwise, as a
    turn would refuse it): the widget hears it at once instead of waiting
    for an answer that never comes. The visitor is identified by the
    widget's random session key; the page's source tag, cut to a tag (or
    dropped), goes with the message. A message has text, uploads
    (`attachment_ids`, POST .../attachments) or both; each upload must be
    the visitor's own, not attached to a message yet and at most a day
    old (404 otherwise); queueing the message claims it.

    The endpoint is public and every message costs a model call, so
    messages are limited per visitor, per client network (an IPv6 /64), per
    business and for the platform before anything is read (429 with
    Retry-After, `WIDGET_MESSAGE_LIMITS`); the caller chooses the session
    key, so the other limits bound the model spend. The website chat notes
    that a visitor wrote (`last_inbound_at`, to the minute).
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        channel_repo: ChannelRepoContract,
        rate_limit_registry: RequestRateLimitRegistryContract,
        wall_clock: WallClock[Microseconds],
        widget_upload_repo: WidgetUploadRepoContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._rate_limit_registry: RequestRateLimitRegistryContract = (
            rate_limit_registry
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._widget_upload_repo: WidgetUploadRepoContract = widget_upload_repo

    def run(self, input_data: WidgetMessageCommand) -> AcceptedWidgetMessage:
        now: Microseconds = self._wall_clock.now_unix()
        refuse_too_frequent_widget_requests(
            self._rate_limit_registry,
            WIDGET_MESSAGE_LIMITS,
            business_id=input_data.business_id,
            session_key=input_data.request.session_key,
            client_ip_address=input_data.client_ip_address,
            now=now,
        )
        if input_data.request.text is None and not input_data.request.attachment_ids:
            raise ValidationFailedError("A message needs text or an attachment.")

        business, channel = find_open_widget_chat(
            self._business_repo, self._channel_repo, input_data.business_id
        )
        require_live_assistant(business)
        uploads: list[WidgetUploadDocument] = read_message_uploads(
            self._widget_upload_repo,
            business.id,
            input_data.request.session_key,
            input_data.request.attachment_ids,
            now,
        )
        stamp_channel_activity(
            self._channel_repo, channel, MessageDirection.INBOUND, now
        )
        return AcceptedWidgetMessage(
            message=self._inbound_message(business, input_data),
            upload_ids=[upload.id for upload in uploads],
            attachments=[inbound_attachment_of(upload) for upload in uploads],
        )

    def _inbound_message(
        self, business: BusinessDocument, input_data: WidgetMessageCommand
    ) -> InboundMessage:
        text: str = (
            "" if input_data.request.text is None else str(input_data.request.text)
        )
        return InboundMessage(
            business_id=business.id,
            channel=ChannelKind.WEB_CHAT,
            channel_user_id=ChannelUserId(str(input_data.request.session_key)),
            text=MessageText(text),
            contact_name=read_contact_name(input_data.request.contact_name),
            acquisition_source=normalize_source(
                None
                if input_data.request.source is None
                else str(input_data.request.source)
            ),
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
