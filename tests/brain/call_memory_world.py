"""
A finished call of the brain world's customer, summarized by the real
`SummarizeCallUseCase` over the world's repositories: a scripted summary
model, staff who get nothing (no staff contacts are needed here).
"""

import json
from dataclasses import dataclass

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.call_follow_up_repositories import CallSettingsRepository
from app.schemas.constants.channel_events import PostCallEventStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.conversations import CallDocument, ConversationDocument
from app.schemas.dto.calls.call_summaries import (
    CallSummaryOutcome,
    CallSummaryRequest,
)
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.dto.notifications.staff_alerts import StaffAlert
from app.schemas.dto.voice_webhooks import FinishedCallTranscriptLine, RecordedCall
from app.schemas.typings.channels.constrained_integers import CallOffsetSeconds
from app.schemas.typings.conversations.strings import (
    ChannelUserId,
    MessageText,
    ProviderCallId,
)
from app.schemas.typings.handoffs.constrained_integers import (
    DeliveredNotificationCount,
)
from app.transformers.notifications.call_report_brief_transformer import (
    CallReportBriefTransformer,
)
from app.transformers.notifications.call_report_text_transformer import (
    CallReportTextTransformer,
)
from app.use_cases.voice.summaries.summarize_call_use_case import (
    SummarizeCallUseCase,
)
from app.utilities.calls.call_follow_up_keys import call_settings_id_of
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.localization.phone_number_parser import PhoneNumberParser
from tests.brain.brain_world import CUSTOMER_PHONE, BrainWorld


class SilentStaff:
    """Staff alerts that reach nobody (the call memory is under test)."""

    def alert(
        self, business: BusinessDocument, alert: StaffAlert, texts: object
    ) -> DeliveredNotificationCount:
        del business, alert, texts
        return DeliveredNotificationCount(0)


@dataclass(frozen=True)
class FinishedCall:
    call: RecordedCall
    conversation: ConversationDocument


def summary_answer(memory: str | None) -> ScriptedLlmTurn:
    """The model's JSON: the owner's summary in Georgian and the memory."""

    answer: dict[str, str] = {"ka": "სტუმარმა მაგიდა დაჯავშნა."}
    if memory is not None:
        answer["memory"] = memory
    return ScriptedLlmTurn(text=MessageText(json.dumps(answer, ensure_ascii=False)))


def finish_call(world: BrainWorld, *, declined: bool = False) -> FinishedCall:
    """The customer called from their phone: the call and its conversation."""

    now = world.clock.wall_clock().now_unix()
    contact = ContactDocument(
        business_id=world.business.id,
        phone_number=CUSTOMER_PHONE,
        verified_phone_number=CUSTOMER_PHONE,
        channel_identities=[
            ChannelIdentity(
                channel=ChannelKind.PHONE,
                channel_user_id=ChannelUserId(str(CUSTOMER_PHONE)),
            )
        ],
        created_at=now,
        updated_at=now,
    )
    world.contact_repo.save(contact)
    conversation = ConversationDocument(
        business_id=world.business.id,
        contact_id=contact.id,
        assistant_version_id=world.version.id,
        channel=ChannelKind.PHONE,
        channel_user_id=ChannelUserId("conv_call_1"),
        last_message_at=now,
        created_at=now,
        updated_at=now,
    )
    world.conversation_repo.save(conversation)
    call = CallDocument(
        business_id=world.business.id,
        conversation_id=conversation.id,
        from_phone_number=CUSTOMER_PHONE,
        started_at=now,
        provider_call_id=ProviderCallId("conv_call_1"),
        recording_declined=declined,
        created_at=now,
        updated_at=now,
    )
    world.call_repo.save(call)
    return FinishedCall(
        call=RecordedCall(
            status=PostCallEventStatus.RECORDED,
            business_id=world.business.id,
            call_id=call.id,
            conversation_id=conversation.id,
            contact_id=contact.id,
            is_recording_declined=declined,
        ),
        conversation=conversation,
    )


def call_transcript(
    *lines: tuple[MessageAuthor, str],
) -> list[FinishedCallTranscriptLine]:
    return [
        FinishedCallTranscriptLine(
            author=author, text=MessageText(text), offset_seconds=CallOffsetSeconds(0)
        )
        for author, text in lines
    ]


def summarize_call(
    world: BrainWorld,
    finished: FinishedCall,
    model: ScriptedLlmAdapter,
    transcript: list[FinishedCallTranscriptLine],
    *,
    is_summary_enabled: bool = True,
) -> CallSummaryOutcome:
    settings_repo = CallSettingsRepository(
        InMemoryDocumentCollectionAdapter(CallSettingsDocument)
    )
    if not is_summary_enabled:
        settings_repo.save(
            CallSettingsDocument(
                id=call_settings_id_of(world.business.id),
                business_id=world.business.id,
                is_summary_enabled=False,
            )
        )
    use_case = SummarizeCallUseCase(
        world.business_repo,
        world.call_repo,
        world.contact_repo,
        world.memory.booking_repo,
        settings_repo,
        model,
        SilentStaff(),
        CallReportTextTransformer(world.texts),
        CallReportBriefTransformer(world.texts),
        PhoneNumberParser(),
        assemble_app_settings({}),
        world.live_events,
        world.clock.wall_clock(),
        world.conversation_repo,
        world.conversation_repo,
        world.memory.settings_repo,
    )
    return use_case.run(CallSummaryRequest(call=finished.call, transcript=transcript))
