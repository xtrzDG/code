import logging

from app.contracts.facilitators import ChannelMessageSenderFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    MessageRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.businesses import BusinessLinkKind
from app.schemas.constants.channel_events import PostCallEventStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.voice_webhooks import RecordedCall
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.channels.booleans import IsCallLinkMessageSent
from app.schemas.typings.conversations.strings import MessageText
from app.utilities.channels.call_links import (
    CALL_LINKS_TEXT,
    build_call_links_text,
    find_promised_link_kinds,
)
from app.utilities.channels.caller_reachability import list_reachable_identities
from app.utilities.knowledge.profile_links import find_profile_link

logger: logging.Logger = logging.getLogger(__name__)


class SendCallLinksUseCase(UseCaseContract[RecordedCall, IsCallLinkMessageSent]):
    """
    After a call, text the caller the links the phone assistant promised
    (concept section 7: links are never read aloud on the phone).

    The promised links are the send_link results of the call that said
    `texted_after_call`; their addresses come from the business profile as
    it is now. One message in the call's language goes to the first
    connected messenger that reaches the caller. A repeated webhook sends
    nothing again; delivery problems are logged and the call stays stored.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        contact_repo: ContactRepoContract,
        channel_repo: ChannelRepoContract,
        message_repo: MessageRepoContract,
        channel_message_sender: ChannelMessageSenderFacilitatorContract,
        text_resolver: LocalizedTextResolverContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._message_repo: MessageRepoContract = message_repo
        self._channel_message_sender: ChannelMessageSenderFacilitatorContract = (
            channel_message_sender
        )
        self._text_resolver: LocalizedTextResolverContract = text_resolver

    def run(self, input_data: RecordedCall) -> IsCallLinkMessageSent:
        if (
            input_data.status is not PostCallEventStatus.RECORDED
            or input_data.business_id is None
            or input_data.conversation_id is None
            or input_data.contact_id is None
        ):
            return False

        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        contact: ContactDocument | None = self._contact_repo.get(
            input_data.business_id, input_data.contact_id
        )
        profile: BusinessProfileDocument | None = (
            self._business_profile_repo.get_by_business(input_data.business_id)
        )
        if business is None or contact is None or profile is None:
            return False

        kinds: list[BusinessLinkKind] = find_promised_link_kinds(
            self._message_repo.list_by_conversation(
                business.id, input_data.conversation_id
            )
        )
        urls: list[str] = []
        for kind in kinds:
            url = find_profile_link(profile, kind)
            if url is not None and str(url) not in urls:
                urls.append(str(url))

        if not urls:
            return False

        header: str = str(
            self._text_resolver.resolve(
                CALL_LINKS_TEXT, input_data.language or business.default_language
            )
        ).format(business=business.name)
        text = MessageText(build_call_links_text(header, urls))
        for identity in list_reachable_identities(
            self._channel_repo, business.id, contact
        ):
            try:
                self._channel_message_sender.send(
                    business.id, identity.channel, identity.channel_user_id, text
                )
            except ExternalServiceError as error:
                logger.warning(
                    "Call links through %s failed: %s", identity.channel.value, error
                )
                continue

            return True

        return False
