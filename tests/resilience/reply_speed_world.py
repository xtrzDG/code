"""
The channels testbed with reply speed switched on: quick messages grouped
(MESSAGE_COALESCE_SECONDS), "typing…" recorded and the real holding reply
of the turn deadline, over a stand-in engine that can think slowly.
"""

import time

from app.contracts.jobs import QueuedJobOperator
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.conversations import AssistantReply, InboundMessage
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.conversations.constrained_integers import (
    ChatTurnDeadlineSeconds,
    MessageCoalesceSeconds,
)
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.platform.constrained_strings import JobName
from app.use_cases.channels.inbox.send_holding_reply_use_case import (
    SendHoldingReplyUseCase,
)
from app.utilities.deliveries.delivery_jobs import PROCESS_INBOUND_MESSAGE_JOB
from tests.channels.channels_deliveries import as_job_operator
from tests.channels.scripted_customer_pipeline import ScriptedCustomerPipeline
from tests.channels.testbed import ChannelsTestbed
from tests.resilience.reply_speed_testbed import (
    RecordingTypingSignals,
    process_inbound_message_orchestrator,
)

COALESCE_SECONDS: MessageCoalesceSeconds = MessageCoalesceSeconds(3)
DEADLINE_SECONDS: ChatTurnDeadlineSeconds = ChatTurnDeadlineSeconds(20)


class PatientPipeline(ScriptedCustomerPipeline):
    """
    Like the engine: the customer's message is stored first, then the model
    thinks (`thinking_seconds` of real time) and the answer, which reads
    every unanswered message, is stored. A deferred message (an earlier one
    of a burst) is only stored. `failures` are raised after thinking, one
    per turn (a provider that timed out).
    """

    def __init__(self, testbed: ChannelsTestbed) -> None:
        super().__init__(testbed.conversation_repo, testbed.message_repo, testbed.clock)
        self.thinking_seconds: float = 0.0
        self.failures: list[ApplicationError] = []
        # The customer's unanswered messages by id (a retried turn stores
        # its message again).
        self.unanswered: dict[str, str] = {}

    def start(self, input_data: InboundMessage) -> AssistantReply:
        self.messages.append(input_data)
        conversation: ConversationDocument = self._conversation_of(input_data)
        self._store(
            conversation,
            MessageAuthor.CUSTOMER,
            input_data.text,
            input_data.customer_message_id,
        )
        self.unanswered[str(input_data.customer_message_id)] = str(input_data.text)
        if input_data.is_reply_deferred:
            return AssistantReply(
                conversation_id=conversation.id,
                text=None,
                language=self.language,
                is_handed_off=False,
            )

        time.sleep(self.thinking_seconds)
        if self.failures:
            raise self.failures.pop(0)

        text = MessageText("Reply to: " + " / ".join(self.unanswered.values()))
        self.unanswered = {}
        self._store(
            conversation, MessageAuthor.ASSISTANT, text, input_data.reply_message_id
        )
        return AssistantReply(
            conversation_id=conversation.id,
            text=text,
            language=self.language,
            is_handed_off=False,
        )


class ReplySpeedTestbed(ChannelsTestbed):
    def __init__(
        self,
        coalesce_seconds: MessageCoalesceSeconds = COALESCE_SECONDS,
        deadline_seconds: ChatTurnDeadlineSeconds = DEADLINE_SECONDS,
    ) -> None:
        super().__init__()
        self.patient = PatientPipeline(self)
        self.pipeline = self.patient
        self.typing = RecordingTypingSignals()
        self.coalesce_seconds: MessageCoalesceSeconds = coalesce_seconds
        self.deadline_seconds: ChatTurnDeadlineSeconds = deadline_seconds
        self.worker = self.build_worker()

    def job_operators(self) -> dict[JobName, QueuedJobOperator]:
        operators = super().job_operators()
        if "patient" not in vars(self):
            return operators  # while the base testbed is built

        operators[PROCESS_INBOUND_MESSAGE_JOB] = as_job_operator(
            process_inbound_message_orchestrator(
                self,
                coalesce_seconds=self.coalesce_seconds,
                typing_signals=self.typing,
                send_holding_reply=SendHoldingReplyUseCase(
                    self.message_repo,
                    self.conversation_repo,
                    self.outbound_message_repo,
                    self.job_queue,
                    self.text_resolver,
                    self.live_events,
                    self.wall_clock,
                ),
                deadline_seconds=self.deadline_seconds,
            )
        )
        return operators
