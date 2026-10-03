"""The invented-numbers guard on what the phone assistant said (after the call)."""

import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.conversation_repositories import (
    CallRepoContract,
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channel_events import PostCallEventStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import CallGuardVerdict, CallOutcome
from app.schemas.constants.handoffs import (
    HandoffReason,
    HandoffSummaryCode,
    HandoffUrgency,
)
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import CallDocument, ConversationDocument
from app.schemas.dto.call_audits import CallAudit, CallAuditRequest
from app.schemas.dto.handoffs import (
    CodedHandoffSummary,
    HandoffCommand,
    HandoffResult,
)
from app.schemas.dto.voice_webhooks import RecordedCall
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.conversations.strings import (
    MessageText,
    UnverifiedReplyValue,
)
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.voice.call_audit_evidence import (
    collect_call_evidence,
    split_call_lines,
)
from app.utilities.reply_guard.invented_numbers import find_unverified_values

LOGGER: logging.Logger = logging.getLogger(__name__)
OUTCOMES_STAFF_CHECK: frozenset[CallOutcome] = frozenset(
    {CallOutcome.BOOKING, CallOutcome.LEAD}
)
MAX_LISTED_VALUES: int = 10


class AuditCallRepliesUseCase(UseCaseContract[CallAuditRequest, CallAudit]):
    """
    Run the invented-numbers guard over the assistant's lines of a call just
    stored (concept section 5): in a call nothing can be rewritten, so the
    result is kept and acted on afterwards.

    Evidence: the business, the facts of the call's version, the call's
    date context, the results of the tools it called and the caller's
    bookings; the caller's own words back times, dates and counts, never a
    price. The call gets `guard_verdict` and `unverified_values`. When a call
    that made a booking or a lead has findings, staff get a low-urgency
    handoff to check what was agreed. A repeated webhook is not audited
    again; a handoff that cannot be opened leaves the call FLAGGED.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        call_repo: CallRepoContract,
        conversation_repo: ConversationRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        message_repo: MessageRepoContract,
        booking_repo: BookingRepoContract,
        handoff_to_human: UseCaseContract[HandoffCommand, HandoffResult],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._call_repo: CallRepoContract = call_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._message_repo: MessageRepoContract = message_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._handoff_to_human: UseCaseContract[HandoffCommand, HandoffResult] = (
            handoff_to_human
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CallAuditRequest) -> CallAudit:
        recorded: RecordedCall = input_data.call
        if (
            recorded.status is not PostCallEventStatus.RECORDED
            or recorded.business_id is None
            or recorded.call_id is None
        ):
            return CallAudit()

        business: BusinessDocument | None = self._business_repo.get(
            recorded.business_id
        )
        call: CallDocument | None = self._call_repo.get(
            recorded.business_id, recorded.call_id
        )
        if business is None or call is None:
            return CallAudit()

        conversation: ConversationDocument | None = (
            None
            if recorded.conversation_id is None
            else self._conversation_repo.get(business.id, recorded.conversation_id)
        )
        version: AssistantVersionDocument | None = self._find_version(
            business, conversation
        )
        values: list[UnverifiedReplyValue] = self._find_values(
            input_data, business, call, conversation, version
        )
        verdict: CallGuardVerdict = CallGuardVerdict.CLEAN
        handoff_id: HandoffId | None = None
        if values:
            handoff_id = self._hand_off(recorded, business, conversation, values)
            verdict = (
                CallGuardVerdict.FLAGGED
                if handoff_id is None
                else CallGuardVerdict.HANDED_OFF
            )

        call.guard_verdict = verdict
        call.unverified_values = values
        call.updated_at = self._wall_clock.now_unix()
        self._call_repo.save(call)
        return CallAudit(
            guard_verdict=verdict, unverified_values=values, handoff_id=handoff_id
        )

    def _find_version(
        self,
        business: BusinessDocument,
        conversation: ConversationDocument | None,
    ) -> AssistantVersionDocument | None:
        """The version the call ran on: its conversation's, else the live one."""

        version_id = (
            conversation.assistant_version_id
            if conversation is not None
            else business.published_assistant_version_id
        )
        if version_id is None:
            return None

        return self._assistant_version_repo.get(business.id, version_id)

    def _find_values(
        self,
        input_data: CallAuditRequest,
        business: BusinessDocument,
        call: CallDocument,
        conversation: ConversationDocument | None,
        version: AssistantVersionDocument | None,
    ) -> list[UnverifiedReplyValue]:
        evidence: list[str] = collect_call_evidence(
            self._message_repo,
            self._booking_repo,
            business,
            call,
            conversation,
            version,
        )
        agent_lines, caller_lines = split_call_lines(input_data.transcript)
        languages: list[LanguageTag] = [
            *(business.languages if version is None else version.languages),
            *([] if input_data.call.language is None else [input_data.call.language]),
        ]
        values: list[UnverifiedReplyValue] = []
        for index, line in enumerate(agent_lines):
            for value in find_unverified_values(
                MessageText(line),
                evidence,
                languages,
                [business.currency_code],
                # What the caller said, and what the agent already repeated.
                customer_texts=[*caller_lines, *agent_lines[:index]],
            ):
                if value not in values:
                    values.append(value)

        return values

    def _hand_off(
        self,
        recorded: RecordedCall,
        business: BusinessDocument,
        conversation: ConversationDocument | None,
        values: list[UnverifiedReplyValue],
    ) -> HandoffId | None:
        """A low-urgency handoff when the call made a booking or a lead."""

        if (
            recorded.outcome not in OUTCOMES_STAFF_CHECK
            or conversation is None
            or recorded.contact_id is None
        ):
            return None

        code: HandoffSummaryCode = (
            HandoffSummaryCode.CALL_BOOKING_UNVERIFIED_VALUES
            if recorded.outcome is CallOutcome.BOOKING
            else HandoffSummaryCode.CALL_REQUEST_UNVERIFIED_VALUES
        )
        try:
            result: HandoffResult = self._handoff_to_human.run(
                HandoffCommand(
                    business_id=business.id,
                    conversation_id=conversation.id,
                    contact_id=recorded.contact_id,
                    reason=HandoffReason.UNVERIFIED_NUMBERS,
                    summary=CodedHandoffSummary(
                        code=code, flagged_values=values[:MAX_LISTED_VALUES]
                    ),
                    urgency=HandoffUrgency.LOW,
                    source_channel=ChannelKind.PHONE,
                    language=recorded.language or business.default_language,
                )
            )
        except ApplicationError:
            LOGGER.exception("The handoff after call %s failed.", recorded.call_id)
            return None

        return result.id
