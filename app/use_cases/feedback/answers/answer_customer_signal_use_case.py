from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.privacy import SuppressionListContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.feedback_repositories import (
    FeedbackRequestRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversation_engine import TurnGate
from app.schemas.constants.feedback import CustomerSignalKind
from app.schemas.dto.conversation_engine import PreparedTurn
from app.schemas.dto.feedback.customer_signals import CustomerSignalReply
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.use_cases.feedback.answers.messaging_preferences import MessagingPreferences
from app.use_cases.feedback.answers.visit_ratings import VisitRatings
from app.utilities.channels.opt_out import read_messaging_preference

# Where unrequested messages go, and so where STOP and ratings come from.
MESSENGER_CHANNELS: frozenset[ChannelKind] = frozenset(
    {
        ChannelKind.TELEGRAM,
        ChannelKind.WHATSAPP,
        ChannelKind.MESSENGER,
        ChannelKind.INSTAGRAM,
    }
)
# A customer past the hourly message limit hears nothing back.
SILENT_GATES: frozenset[TurnGate] = frozenset(
    {TurnGate.LIMIT_NOTICE, TurnGate.LIMIT_SILENCE}
)


class AnswerCustomerSignalUseCase(
    UseCaseContract[PreparedTurn, CustomerSignalReply | None]
):
    """
    Messages the platform answers itself, before the assistant: STOP (or
    its translation, as the whole message) stops the messages the customer
    did not ask for, START brings them back, and a rating (1 to 5) right
    after a request for feedback is recorded, thanked with the Google
    review invitation, and for 3 or below hands the conversation to a
    colleague. None for every other message (the assistant answers).

    Only messenger conversations (where unrequested messages go), never
    the owner's test chat. While staff own the conversation the signal is
    still answered (it is the platform's own exchange, not the assistant
    talking); past the hourly limit it is recorded silently.
    """

    def __init__(
        self,
        contact_repo: ContactRepoContract,
        audit_log_repo: AuditLogRepoContract,
        feedback_request_repo: FeedbackRequestRepoContract,
        message_repo: MessageRepoContract,
        profile_repo: BusinessProfileRepoContract,
        text_resolver: LocalizedTextResolverContract,
        wall_clock: WallClock[Microseconds],
        app_base_url: PublicBaseUrl | None,
        suppression_list: SuppressionListContract,
    ) -> None:
        self._preferences: MessagingPreferences = MessagingPreferences(
            contact_repo, audit_log_repo, text_resolver, suppression_list
        )
        self._ratings: VisitRatings = VisitRatings(
            feedback_request_repo,
            message_repo,
            profile_repo,
            text_resolver,
            app_base_url,
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PreparedTurn) -> CustomerSignalReply | None:
        if (
            input_data.conversation.is_sandbox
            or input_data.conversation.channel not in MESSENGER_CHANNELS
        ):
            return None

        now: Microseconds = self._wall_clock.now_unix()
        preference: CustomerSignalKind | None = read_messaging_preference(
            str(input_data.customer_text)
        )
        reply: CustomerSignalReply | None = (
            self._ratings.answer(input_data, now)
            if preference is None
            else self._preferences.apply(input_data, preference, now)
        )
        if reply is None or input_data.gate not in SILENT_GATES:
            return reply

        return reply.model_copy(update={"text": None})
