from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.conversation_review_contracts import (
    ConversationReviewRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.conversations import ConversationRating, MessageAuthor
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.conversation_feed.answer_reviews import ConversationRatingChange
from app.schemas.dto.conversation_feed.conversation_actions import (
    RateConversationCommand,
)
from app.schemas.dto.conversation_feed.conversation_views import (
    ConversationSummaryView,
    ConversationViewSource,
)
from app.schemas.dto.paging import KeysetSlice
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.use_cases.conversations.feed.conversation_rows import build_view_sources

# The latest answer a bad rating is about is among the newest messages.
LATEST_ANSWER_LOOKBACK: KeysetReadLimit = KeysetReadLimit(10)


class RateConversationUseCase(
    UseCaseContract[RateConversationCommand, ConversationSummaryView]
):
    """
    Owner or staff marks how the assistant handled a conversation, good or
    bad (concept section 8, the conversation card), for the weekly quality
    review (section 11). A bad rating may say why (wrong information, should
    have passed it to a person, tone, too long) and names the assistant
    answer it is about (the latest one unless the cabinet names one); until
    someone corrects an answer or saves a check from it, it waits in the
    Overview's "Answers worth improving". Who rated and when is kept; null
    clears it. The rating is its own write, so a customer turn answered
    meanwhile never undoes it.

    Raises:
        NotFoundError: the conversation or the named answer is missing.
        ValidationFailedError: a reason without a bad rating, or a named
            message that is not the assistant's answer.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        conversation_repo: ConversationRepoContract,
        conversation_review_repo: ConversationReviewRepoContract,
        contact_repo: ContactRepoContract,
        message_repo: MessageRepoContract,
        summary_transformer: TransformerContract[
            ConversationViewSource, ConversationSummaryView
        ],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._conversation_review_repo: ConversationReviewRepoContract = (
            conversation_review_repo
        )
        self._contact_repo: ContactRepoContract = contact_repo
        self._message_repo: MessageRepoContract = message_repo
        self._summary_transformer: TransformerContract[
            ConversationViewSource, ConversationSummaryView
        ] = summary_transformer
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: RateConversationCommand) -> ConversationSummaryView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        conversation: ConversationDocument | None = self._conversation_repo.get(
            business.id, input_data.conversation_id
        )
        if conversation is None:
            raise NotFoundError(
                f"Conversation {input_data.conversation_id} was not found."
            )

        is_bad: bool = input_data.rating is ConversationRating.BAD
        if input_data.reason is not None and not is_bad:
            raise ValidationFailedError("Only a bad rating says what was wrong.")

        rated: ConversationDocument | None = self._conversation_review_repo.set_rating(
            business.id,
            conversation.id,
            ConversationRatingChange(
                rating=input_data.rating,
                rated_by=input_data.user_id,
                rating_reason=input_data.reason,
                rated_message_id=(
                    self._rated_answer(conversation, input_data.message_id)
                    if is_bad
                    else None
                ),
                at=self._wall_clock.now_unix(),
            ),
        )
        return self._summary_transformer.transform(
            build_view_sources(
                business.id,
                [rated or conversation],
                self._contact_repo,
                self._message_repo,
            )[0]
        )

    def _rated_answer(
        self, conversation: ConversationDocument, message_id: MessageId | None
    ) -> MessageId | None:
        """The named assistant answer, else the latest one (None: none yet)."""

        if message_id is None:
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

        message: MessageDocument | None = self._message_repo.get(
            conversation.business_id, message_id
        )
        if message is None or message.conversation_id != conversation.id:
            raise NotFoundError(f"Message {message_id} was not found.")

        if message.author is not MessageAuthor.ASSISTANT:
            raise ValidationFailedError("A rating is about an answer of the assistant.")

        return message.id
