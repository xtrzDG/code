from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
)
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    MessageRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.businesses import BusinessLinkKind
from app.schemas.constants.channel_events import PostCallEventStatus
from app.schemas.constants.deliveries import OutboundMessageKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.voice_webhooks import RecordedCall
from app.schemas.typings.channels.booleans import IsCallLinkMessageSent
from app.schemas.typings.conversations.strings import MessageText
from app.use_cases.voice.call_message_outbox import CallMessageOutbox
from app.utilities.channels.call_links import (
    CALL_LINKS_TEXT,
    build_call_links_text,
    find_promised_link_kinds,
)
from app.utilities.knowledge.profile_links import find_profile_link


class SendCallLinksUseCase(UseCaseContract[RecordedCall, IsCallLinkMessageSent]):
    """
    After a call, text the caller the links the phone assistant promised
    (concept section 7: links are never read aloud on the phone).

    The promised links are the send_link results of the call that said
    `texted_after_call`; their addresses come from the business profile as
    it is now. One message in the call's language goes into the outbox for
    the first connected messenger that can reach the caller now
    (`CallMessageOutbox`), once per call, and the worker sends it with
    retries. A repeated webhook sends nothing again; True when it was
    queued.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        contact_repo: ContactRepoContract,
        message_repo: MessageRepoContract,
        call_messages: CallMessageOutbox,
        text_resolver: LocalizedTextResolverContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._message_repo: MessageRepoContract = message_repo
        self._call_messages: CallMessageOutbox = call_messages
        self._text_resolver: LocalizedTextResolverContract = text_resolver

    def run(self, input_data: RecordedCall) -> IsCallLinkMessageSent:
        if (
            input_data.status is not PostCallEventStatus.RECORDED
            or input_data.business_id is None
            or input_data.call_id is None
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
        return self._call_messages.queue(
            business, contact, input_data.call_id, OutboundMessageKind.CALL_LINKS, text
        )
