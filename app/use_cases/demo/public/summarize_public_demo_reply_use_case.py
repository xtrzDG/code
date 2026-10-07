from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.conversation_repositories import MessageRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import MessageDirection
from app.schemas.dto.public_demo import PublicDemoReply, PublicDemoTurnOutcome
from app.schemas.typings.public_site.constrained_integers import (
    PublicDemoMessagesLeft,
)
from app.utilities.public_site.public_demo_limits import (
    PUBLIC_DEMO_MESSAGES_PER_CONVERSATION,
    PUBLIC_DEMO_WINDOW_SECONDS,
)

MICROSECONDS_PER_SECOND: int = 1_000_000


class SummarizePublicDemoReplyUseCase(
    UseCaseContract[PublicDemoTurnOutcome, PublicDemoReply]
):
    """
    What the visitor of a demo sees after a turn: the assistant's answer,
    whether it made a (sandbox) booking, took down a request or passed the
    conversation to a person, and how many messages the visitor may still
    send in this hour (the visitor's messages of the last hour counted in
    the conversation).
    """

    def __init__(
        self,
        message_repo: MessageRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._message_repo: MessageRepoContract = message_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PublicDemoTurnOutcome) -> PublicDemoReply:
        reply = input_data.reply
        hour_ago = Microseconds(
            self._wall_clock.now_unix()
            - int(PUBLIC_DEMO_WINDOW_SECONDS) * MICROSECONDS_PER_SECOND
        )
        sent: int = int(
            self._message_repo.count_by_conversation(
                input_data.business_id,
                reply.conversation_id,
                MessageDirection.INBOUND,
                created_from=hour_ago,
            )
        )
        return PublicDemoReply(
            text=reply.text,
            language=reply.language,
            is_booking_made=reply.created_booking_ids != [],
            is_request_made=reply.created_lead_ids != [],
            is_handoff_made=reply.is_handed_off or reply.created_handoff_ids != [],
            messages_left=PublicDemoMessagesLeft(
                max(0, PUBLIC_DEMO_MESSAGES_PER_CONVERSATION - sent)
            ),
        )
