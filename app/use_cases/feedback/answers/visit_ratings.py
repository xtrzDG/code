"""
A customer's rating of their visit, read from their reply to the request
for feedback: recorded once on the request, thanked in their language with
the same invitation to the business's Google review page whatever the
rating (no review gating), and, for a rating of 3 or below, a low-urgency
handoff so a colleague gets in touch.
"""

from dataclasses import dataclass
from datetime import timedelta

from typed_time_provider import Microseconds

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
)
from app.contracts.repositories.conversation_repositories import MessageRepoContract
from app.contracts.repositories.feedback_repositories import (
    FeedbackRequestRepoContract,
)
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.constants.feedback import CustomerSignalKind, FeedbackRequestStatus
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.domain.feedback import FeedbackRequestDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.conversation_engine import PreparedTurn
from app.schemas.dto.feedback.customer_signals import CustomerSignalReply
from app.schemas.dto.handoffs import HandoffCommand
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.feedback.constrained_integers import VisitScore
from app.schemas.typings.handoffs.strings import HandoffSummary
from app.utilities.feedback.feedback_keys import review_redirect_url
from app.utilities.feedback.feedback_reply_texts import (
    FEEDBACK_SORRY_TEXT,
    FEEDBACK_THANKS_TEXT,
    LINK_FIELD,
    REVIEW_INVITE_TEXT,
)
from app.utilities.feedback.feedback_staff_texts import LOW_RATING_SUMMARY
from app.utilities.feedback.visit_scores import parse_visit_score
from app.utilities.localization.language_tags import base_language_code

MICROSECONDS_PER_SECOND: int = 1_000_000
# A rating answers a request sent in the last week.
ANSWER_WINDOW: timedelta = timedelta(days=7)
LOW_SCORE_LIMIT: int = 3
MAX_QUOTED_WORDS: int = 300
PARAGRAPH: str = "\n\n"


@dataclass(frozen=True)
class VisitRatings:
    feedback_request_repo: FeedbackRequestRepoContract
    message_repo: MessageRepoContract
    profile_repo: BusinessProfileRepoContract
    text_resolver: LocalizedTextResolverContract
    app_base_url: PublicBaseUrl | None

    def answer(
        self, turn: PreparedTurn, now: Microseconds
    ) -> CustomerSignalReply | None:
        """The reply to a rating; None when the message is not one."""

        languages: set[str] = {
            base_language_code(language)
            for language in (turn.language, *turn.business.languages)
        }
        score: VisitScore | None = parse_visit_score(str(turn.customer_text), languages)
        if score is None:
            return None

        request: FeedbackRequestDocument | None = self._waiting_request(turn, now)
        if request is None:
            return None

        answered: FeedbackRequestDocument | None = self._record(
            request, score, turn, now
        )
        if answered is None:
            return None

        return CustomerSignalReply(
            kind=CustomerSignalKind.VISIT_SCORE,
            text=self._reply_text(turn, answered, score),
            handoff=low_rating_handoff(turn, score, self._staff_summary(turn, score)),
        )

    def _waiting_request(
        self, turn: PreparedTurn, now: Microseconds
    ) -> FeedbackRequestDocument | None:
        """
        The customer's newest request still waiting, sent in this channel
        within the week, when nothing was written to them since: once the
        assistant or staff wrote, a number answers them, not the request.
        """

        window_start: int = int(now) - int(ANSWER_WINDOW.total_seconds()) * (
            MICROSECONDS_PER_SECOND
        )
        for request in self.feedback_request_repo.list_waiting(
            turn.business.id, turn.contact.id
        ):
            if (
                request.channel is not turn.conversation.channel
                or request.sent_at is None
                or int(request.sent_at) < window_start
            ):
                continue

            written_since = self.message_repo.count_by_conversation(
                turn.business.id,
                turn.conversation.id,
                MessageDirection.OUTBOUND,
                created_from=Microseconds(int(request.sent_at) + 1),
            )
            return request if int(written_since) == 0 else None

        return None

    def _record(
        self,
        request: FeedbackRequestDocument,
        score: VisitScore,
        turn: PreparedTurn,
        now: Microseconds,
    ) -> FeedbackRequestDocument | None:
        def answer(current: FeedbackRequestDocument) -> FeedbackRequestDocument | None:
            if current.status is not FeedbackRequestStatus.SENT:
                return None

            current.status = FeedbackRequestStatus.ANSWERED
            current.score = score
            current.answered_at = now
            current.conversation_id = turn.conversation.id
            current.updated_at = now
            return current

        return self.feedback_request_repo.update(turn.business.id, request.id, answer)

    def _reply_text(
        self,
        turn: PreparedTurn,
        request: FeedbackRequestDocument,
        score: VisitScore,
    ) -> MessageText:
        thanks = (
            FEEDBACK_THANKS_TEXT if score > LOW_SCORE_LIMIT else FEEDBACK_SORRY_TEXT
        )
        paragraphs: list[str] = [str(self.text_resolver.resolve(thanks, turn.language))]
        link: str | None = self._review_link(turn, request)
        if link is not None:
            invite: str = str(
                self.text_resolver.resolve(REVIEW_INVITE_TEXT, turn.language)
            )
            paragraphs.append(invite.replace(LINK_FIELD, link))

        return MessageText(PARAGRAPH.join(paragraphs))

    def _review_link(
        self, turn: PreparedTurn, request: FeedbackRequestDocument
    ) -> str | None:
        """
        The platform's counting address of the business's review page, or
        the page itself when the platform's public address is not set.
        """

        profile: BusinessProfileDocument | None = self.profile_repo.get_by_business(
            turn.business.id
        )
        if profile is None or profile.google_review_url is None:
            return None

        if self.app_base_url is None or request.review_token is None:
            return str(profile.google_review_url)

        return str(review_redirect_url(self.app_base_url, request.review_token))

    def _staff_summary(self, turn: PreparedTurn, score: VisitScore) -> HandoffSummary:
        template: str = str(
            self.text_resolver.resolve(LOW_RATING_SUMMARY, turn.business.owner_language)
        )
        words: str = str(turn.customer_text).strip()[:MAX_QUOTED_WORDS]
        return HandoffSummary(template.format(score=int(score), words=words))


def low_rating_handoff(
    turn: PreparedTurn,
    score: VisitScore,
    summary: HandoffSummary,
) -> HandoffCommand | None:
    """A colleague gets in touch after a rating of 3 or below (once)."""

    if (
        score > LOW_SCORE_LIMIT
        or turn.conversation.status is ConversationStatus.HANDOFF
    ):
        return None

    return HandoffCommand(
        business_id=turn.business.id,
        conversation_id=turn.conversation.id,
        contact_id=turn.contact.id,
        reason=HandoffReason.COMPLAINT,
        summary=summary,
        urgency=HandoffUrgency.LOW,
        source_channel=turn.conversation.channel,
        language=turn.language,
        is_sandbox=turn.conversation.is_sandbox,
    )
