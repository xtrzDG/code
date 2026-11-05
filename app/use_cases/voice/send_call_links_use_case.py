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
from app.schemas.dto.calls.call_summaries import CallSummaryRequest
from app.schemas.dto.voice_webhooks import RecordedCall
from app.schemas.typings.channels.booleans import IsCallLinkMessageSent
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.use_cases.voice.call_message_outbox import CallMessageOutbox
from app.utilities.channels.call_links import (
    CALL_LINKS_TEXT,
    build_call_links_text,
    find_promised_link_kinds,
)
from app.utilities.channels.call_transcript_message import (
    CALL_TRANSCRIPT_TEXT,
    CALLER_LABEL_TEXT,
    build_call_transcript_text,
)
from app.utilities.knowledge.profile_links import find_sendable_link


class SendCallLinksUseCase(UseCaseContract[CallSummaryRequest, IsCallLinkMessageSent]):
    """
    After a call, text the caller the links the phone assistant promised
    (concept section 7: links are never read aloud on the phone) and, when
    they asked for it (send_call_transcript, ACC-03), the call's transcript.

    The promised links are the send_link results of the call that said
    `texted_after_call`; their addresses come from the business profile as
    it is now (the privacy notice, without one of the business's own, from
    the platform's hosted notice, as send_link gave it). The transcript is
    the one the voice platform reported (`call_transcript_message`). One
    message in the call's language goes into the outbox for the first
    connected messenger that can reach the caller now
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
        cabinet_base_url: CabinetBaseUrl | None,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._message_repo: MessageRepoContract = message_repo
        self._call_messages: CallMessageOutbox = call_messages
        self._text_resolver: LocalizedTextResolverContract = text_resolver
        self._cabinet_base_url: CabinetBaseUrl | None = cabinet_base_url

    def run(self, input_data: CallSummaryRequest) -> IsCallLinkMessageSent:
        recorded: RecordedCall = input_data.call
        if (
            recorded.status is not PostCallEventStatus.RECORDED
            or recorded.business_id is None
            or recorded.call_id is None
            or recorded.conversation_id is None
            or recorded.contact_id is None
        ):
            return False

        business: BusinessDocument | None = self._business_repo.get(
            recorded.business_id
        )
        contact: ContactDocument | None = self._contact_repo.get(
            recorded.business_id, recorded.contact_id
        )
        if business is None or contact is None:
            return False

        language: LanguageTag = recorded.language or business.default_language
        parts: list[str] = []
        urls: list[str] = self._promised_urls(business, recorded)
        if urls:
            header: str = str(
                self._text_resolver.resolve(CALL_LINKS_TEXT, language)
            ).format(business=business.name)
            parts.append(build_call_links_text(header, urls))

        transcript: str | None = (
            build_call_transcript_text(
                str(self._text_resolver.resolve(CALL_TRANSCRIPT_TEXT, language)).format(
                    business=business.name
                ),
                str(self._text_resolver.resolve(CALLER_LABEL_TEXT, language)),
                str(business.name),
                input_data.transcript,
                recorded.is_recording_declined,
            )
            if recorded.is_transcript_requested
            else None
        )
        if transcript is not None:
            parts.append(transcript)

        if not parts:
            return False

        return self._call_messages.queue(
            business,
            contact,
            recorded.call_id,
            OutboundMessageKind.CALL_LINKS,
            MessageText("\n\n".join(parts)),
        )

    def _promised_urls(
        self, business: BusinessDocument, recorded: RecordedCall
    ) -> list[str]:
        if recorded.conversation_id is None:
            return []

        profile: BusinessProfileDocument | None = (
            self._business_profile_repo.get_by_business(business.id)
        )
        kinds: list[BusinessLinkKind] = find_promised_link_kinds(
            self._message_repo.list_by_conversation(
                business.id, recorded.conversation_id
            )
        )
        urls: list[str] = []
        for kind in kinds:
            url = find_sendable_link(business, profile, kind, self._cabinet_base_url)
            if url is not None and str(url) not in urls:
                urls.append(str(url))

        return urls
