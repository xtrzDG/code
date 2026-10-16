from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.business_repositories import (
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.conversation_review_contracts import (
    ConversationReviewRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import ConversationRating, MessageAuthor
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.channels.widget_ratings import (
    WidgetRatingCommand,
    WidgetRatingView,
)
from app.schemas.dto.conversation_feed.answer_reviews import CustomerRatingChange
from app.schemas.dto.paging import KeysetSlice
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.use_cases.shared.widget_chats import require_open_widget_chat
from app.utilities.channels.widget_rate_limits import (
    WIDGET_RATING_LIMITS,
    refuse_too_frequent_widget_requests,
)

# The latest answer a bad rating is about is among the newest messages.
LATEST_ANSWER_LOOKBACK: KeysetReadLimit = KeysetReadLimit(10)
NOTHING_TO_RATE: str = "There is no answer to rate yet."


class RateWidgetConversationUseCase(
    UseCaseContract[WidgetRatingCommand, WidgetRatingView]
):
    """
    A website visitor rates the chat with the thumbs under its answers:
    good or bad, why it was bad (optional), about the answer named (one of
    the assistant's answers in the visitor's own conversations) or the
    latest answer of their current conversation. The visitor is the
    widget's session key, so no other conversation can be named: an answer
    of another conversation, another visitor or business is not found
    (404, the same answer for each).

    The rating is the customer's (`rating_by` CUSTOMER, no `rated_by`): a
    bad one joins the Overview's "Answers worth improving" like the team's.
    It never replaces a rating the team gave (the team's verdict stands,
    and the answer does not tell the visitor). Ratings are limited per
    visitor, per client network, per business and for the platform (429
    with Retry-After, `WIDGET_RATING_LIMITS`), counted before anything is
    read; the chat must be switched on (404).
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        channel_repo: ChannelRepoContract,
        conversation_repo: ConversationRepoContract,
        conversation_review_repo: ConversationReviewRepoContract,
        message_repo: MessageRepoContract,
        rate_limit_registry: RequestRateLimitRegistryContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._conversation_review_repo: ConversationReviewRepoContract = (
            conversation_review_repo
        )
        self._message_repo: MessageRepoContract = message_repo
        self._rate_limit_registry: RequestRateLimitRegistryContract = (
            rate_limit_registry
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: WidgetRatingCommand) -> WidgetRatingView:
        now: Microseconds = self._wall_clock.now_unix()
        request = input_data.request
        refuse_too_frequent_widget_requests(
            self._rate_limit_registry,
            WIDGET_RATING_LIMITS,
            business_id=input_data.business_id,
            session_key=request.session_key,
            client_ip_address=input_data.client_ip_address,
            now=now,
        )
        is_bad: bool = request.rating is ConversationRating.BAD
        if request.reason is not None and not is_bad:
            raise ValidationFailedError("Only a bad rating says what was wrong.")

        business: BusinessDocument = require_open_widget_chat(
            self._business_repo, self._channel_repo, input_data.business_id
        )
        conversations: list[ConversationDocument] = [
            conversation
            for conversation in self._conversation_repo.list_by_channel_user(
                business.id,
                ChannelKind.WEB_CHAT,
                ChannelUserId(str(request.session_key)),
            )
            if not conversation.is_sandbox
        ]
        conversation, answer_id = self._rated(conversations, request.message_id)
        self._conversation_review_repo.set_customer_rating(
            business.id,
            conversation.id,
            CustomerRatingChange(
                rating=request.rating,
                rating_reason=request.reason,
                rated_message_id=answer_id if is_bad else None,
                at=now,
            ),
        )
        return WidgetRatingView(rating=request.rating, reason=request.reason)

    def _rated(
        self,
        conversations: list[ConversationDocument],
        message_id: MessageId | None,
    ) -> tuple[ConversationDocument, MessageId | None]:
        """
        The rated conversation and answer: the named answer's, or the
        current conversation and its latest answer.

        Raises:
            NotFoundError: no conversation yet, or a named message that is
                not an assistant answer of the visitor's conversations.
        """

        if not conversations:
            raise NotFoundError(NOTHING_TO_RATE)

        if message_id is None:
            current: ConversationDocument = conversations[0]
            return current, self._latest_answer(current)

        message: MessageDocument | None = self._message_repo.get(
            conversations[0].business_id, message_id
        )
        own: dict[str, ConversationDocument] = {
            str(conversation.id): conversation for conversation in conversations
        }
        rated: ConversationDocument | None = (
            None if message is None else own.get(str(message.conversation_id))
        )
        if (
            message is None
            or rated is None
            or message.author is not MessageAuthor.ASSISTANT
        ):
            raise NotFoundError(f"Message {message_id} was not found.")

        return rated, message.id

    def _latest_answer(self, conversation: ConversationDocument) -> MessageId | None:
        newest: list[MessageDocument] = self._message_repo.page_transcript(
            conversation.business_id,
            conversation.id,
            KeysetSlice(limit=LATEST_ANSWER_LOOKBACK),
        )
        return next(
            (
                message.id
                for message in newest
                if message.author is MessageAuthor.ASSISTANT
            ),
            None,
        )
