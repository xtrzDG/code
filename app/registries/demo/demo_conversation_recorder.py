from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.registries.demo.demo_clock import DemoClock
from app.registries.demo.demo_media_lines import record_line_media
from app.registries.demo.demo_messages import demo_message
from app.registries.demo.demo_reply_speed import demo_line_pause_microseconds
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import (
    CallGuardVerdict,
    CallOutcome,
    ConversationRating,
    ConversationRatingReason,
    ConversationStatus,
    MessageAuthor,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.conversations import (
    CallDocument,
    CallSummary,
    ConversationDocument,
    MessageDocument,
)
from app.schemas.domain.message_media import MessageAttachment
from app.schemas.domain.profiles import OpeningInterval
from app.schemas.domain.resources import ScheduleExceptionDocument
from app.schemas.dto.demo_data import DemoMediaFile, DemoMessageLine
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.calls.constrained_strings import CallSummaryText
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.constrained_integers import (
    CallDurationSeconds,
)
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.conversations.strings import (
    CallTranscriptText,
    ChannelUserId,
    ProviderCallId,
)
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.scheduling.opening_hours import business_day_ranges, is_open_at
from app.utilities.scheduling.zoned_time import load_time_zone, microseconds_to_seconds


class DemoConversationRecorder:
    """
    Customers of a demo business and what they wrote: conversations with
    their messages (assistant replies carry tool calls, model usage and
    cost) and phone calls with transcripts. Conversations started outside
    the opening hours are flagged as after-hours, as the engine does.
    """

    def __init__(
        self,
        business: BusinessDocument,
        clock: DemoClock,
        hours: list[OpeningInterval],
        schedule_exceptions: list[ScheduleExceptionDocument],
        live_versions: list[tuple[Microseconds, AssistantVersionId]],
        model_id: LlmModelId,
        team_member_id: UserId,
    ) -> None:
        self._business: BusinessDocument = business
        self._clock: DemoClock = clock
        self._live_versions: list[tuple[Microseconds, AssistantVersionId]] = sorted(
            live_versions
        )
        self._model_id: LlmModelId = model_id
        self._team_member_id: UserId = team_member_id
        self._day_ranges = business_day_ranges(hours, schedule_exceptions)
        self.contacts: list[ContactDocument] = []
        self.conversations: list[ConversationDocument] = []
        self.messages: list[MessageDocument] = []
        self.calls: list[CallDocument] = []
        self.media_files: list[DemoMediaFile] = []

    def contact(
        self,
        name: str | None,
        language: str,
        identities: Sequence[tuple[ChannelKind, str]] = (),
        phone: str | None = None,
        is_phone_verified: bool = False,
        since: Microseconds | None = None,
    ) -> ContactDocument:
        moment: Microseconds = since or self._clock.ago(days=30)
        contact = ContactDocument(
            business_id=self._business.id,
            name=None if name is None else ContactName(name),
            phone_number=None if phone is None else E164PhoneNumber(phone),
            verified_phone_number=(
                E164PhoneNumber(phone)
                if phone is not None and is_phone_verified
                else None
            ),
            language=LanguageTag(language),
            channel_identities=[
                ChannelIdentity(channel=channel, channel_user_id=ChannelUserId(user_id))
                for channel, user_id in identities
            ],
            created_at=moment,
            updated_at=moment,
        )
        self.contacts.append(contact)
        return contact

    def chat(
        self,
        contact: ContactDocument,
        channel: ChannelKind,
        start: Microseconds,
        lines: Sequence[DemoMessageLine],
        status: ConversationStatus = ConversationStatus.CLOSED,
        rating: ConversationRating | None = None,
        rated_by: UserId | None = None,
        rating_reason: ConversationRatingReason | None = None,
        channel_user_id: str | None = None,
        is_sandbox: bool = False,
    ) -> ConversationDocument:
        """A conversation whose first line is at `start`."""

        language: LanguageTag | None = contact.language
        conversation = ConversationDocument(
            business_id=self._business.id,
            contact_id=contact.id,
            assistant_version_id=self._version_live_at(start),
            channel=channel,
            channel_user_id=ChannelUserId(
                channel_user_id or self._identity_of(contact, channel)
            ),
            language=language,
            status=status,
            is_after_hours=not is_sandbox
            and not is_open_at(
                microseconds_to_seconds(int(start)),
                load_time_zone(self._business.timezone),
                self._day_ranges,
            ),
            is_sandbox=is_sandbox,
            last_message_at=start,
            created_at=start,
            updated_at=start,
        )
        moment: int = int(start)
        for index, line in enumerate(lines):
            if index > 0:
                moment += demo_line_pause_microseconds(conversation, line, index)
            self.messages.append(
                self._message(conversation, line, index, Microseconds(moment))
            )

        conversation.last_message_at = Microseconds(moment)
        conversation.updated_at = Microseconds(moment)
        if rating is not None:
            conversation.rating = rating
            conversation.rated_by = rated_by
            conversation.rated_at = self._clock.later(Microseconds(moment), 90)
            conversation.rating_reason = rating_reason
            conversation.rated_message_id = next(
                (
                    message.id
                    for message in reversed(self.messages)
                    if message.conversation_id == conversation.id
                    and message.author is MessageAuthor.ASSISTANT
                ),
                None,
            )

        if moment > int(self._clock.now):
            raise ValueError(f"A demo conversation ends in the future: {lines[-1]}")

        self.conversations.append(conversation)
        return conversation

    def call(
        self,
        conversation: ConversationDocument,
        caller: str,
        assistant_line: str,
        duration_seconds: int,
        transcript: Sequence[tuple[int, MessageAuthor, str]],
        outcome: CallOutcome,
        cost_micro_usd: int,
        guard_verdict: CallGuardVerdict | None = None,
        summaries: Sequence[tuple[str, str]] = (),
    ) -> CallDocument:
        """
        A finished call of a phone conversation; lines "[mm:ss] who: text";
        `guard_verdict` is what the after-call check found in it, and
        `summaries` (language, text) what staff were sent after it.
        """

        lines: list[str] = [
            f"[{offset // 60:02d}:{offset % 60:02d}] {author.value}: {text}"
            for offset, author, text in transcript
        ]
        call = CallDocument(
            business_id=self._business.id,
            conversation_id=conversation.id,
            from_phone_number=E164PhoneNumber(caller),
            to_phone_number=E164PhoneNumber(assistant_line),
            started_at=conversation.created_at,
            duration_seconds=CallDurationSeconds(duration_seconds),
            transcript=CallTranscriptText("\n".join(lines)),
            provider_call_id=ProviderCallId(str(conversation.channel_user_id)),
            cost_micro_usd=CostMicroUsd(cost_micro_usd),
            outcome=outcome,
            guard_verdict=guard_verdict,
            summaries=[
                CallSummary(language=LanguageTag(language), text=CallSummaryText(text))
                for language, text in summaries
            ],
            summarized_at=conversation.last_message_at if summaries else None,
            created_at=conversation.created_at,
            updated_at=conversation.last_message_at,
        )
        self.calls.append(call)
        return call

    def _message(
        self,
        conversation: ConversationDocument,
        line: DemoMessageLine,
        position: int,
        moment: Microseconds,
    ) -> MessageDocument:
        message_id = MessageId()
        attachments: list[MessageAttachment]
        attachments, files = record_line_media(
            self._business.id, message_id, line, moment
        )
        self.media_files.extend(files)
        return demo_message(
            conversation,
            line,
            position,
            moment,
            message_id,
            attachments,
            self._model_id,
            self._team_member_id,
        )

    def _version_live_at(self, moment: Microseconds) -> AssistantVersionId:
        """The version published last before `moment` (the first one before)."""

        live: AssistantVersionId = self._live_versions[0][1]
        for published_at, version_id in self._live_versions:
            if published_at <= moment:
                live = version_id

        return live

    def _identity_of(self, contact: ContactDocument, channel: ChannelKind) -> str:
        for identity in contact.channel_identities:
            if identity.channel is channel:
                return str(identity.channel_user_id)

        raise ValueError(f"Demo contact {contact.name} is not known in {channel}.")
