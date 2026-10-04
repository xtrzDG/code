"""The reply of a turn after the guard's review: clean, rewritten or handed over."""

from app.schemas.constants.conversations import ReplyGuardVerdict
from app.schemas.dto.conversation_engine import GeneratedReply, PreparedTurn
from app.schemas.typings.conversations.strings import MessageText
from app.use_cases.conversations.replies.reply_review import ReplyReview
from app.use_cases.conversations.replies.turn_progress import (
    TurnProgress,
    build_reply,
)


def clean_reply(
    turn: PreparedTurn, progress: TurnProgress, text: MessageText, review: ReplyReview
) -> GeneratedReply:
    """A reply the guard let through; its checked claims are kept."""

    return build_reply(
        turn,
        progress,
        text=text,
        claim_findings=list(review.claim_findings),
        verifier_usage=list(review.verifier_usage),
    )


def rewritten_reply(
    turn: PreparedTurn,
    progress: TurnProgress,
    text: MessageText,
    first: ReplyReview,
    second: ReplyReview,
) -> GeneratedReply:
    """
    The rewritten reply, with what the guard found in the first one (the
    values, claims and reasons that made it ask for the rewrite).
    """

    return build_reply(
        turn,
        progress,
        text=text,
        guard_verdict=ReplyGuardVerdict.REWRITTEN,
        guard_reasons=first.reasons,
        unverified_values=list(first.unverified_values),
        claim_findings=list(first.claim_findings),
        verifier_usage=[*first.verifier_usage, *second.verifier_usage],
    )


def handed_off_reply(
    turn: PreparedTurn,
    progress: TurnProgress,
    first: ReplyReview,
    second: ReplyReview | None,
) -> GeneratedReply:
    """
    No reply: the rewrite failed or still had what the guard holds back.
    What the last review found decides the failure (another person's
    contact details first, then values, then claims).
    """

    final: ReplyReview = first if second is None else second
    return build_reply(
        turn,
        progress,
        failure=final.failure,
        guard_verdict=ReplyGuardVerdict.HANDED_OFF,
        guard_reasons=final.reasons,
        unverified_values=list(final.unverified_values),
        claim_findings=list(final.claim_findings),
        verifier_usage=[
            *first.verifier_usage,
            *([] if second is None else second.verifier_usage),
        ],
    )
