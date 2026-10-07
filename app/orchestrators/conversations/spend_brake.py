"""
The spend guard in a conversation turn: before the model answers, the
business's spend of its day decides whether it answers on its own model,
on a cheaper one (past the soft limit), or not at all (past the hard one:
the conversation goes to the team, the customer hears so).

Past the hard limit the handoff carries the code of an unavailable model
(staff read "the assistant could not answer") and the customer's text: a
code of its own comes only in a release after the one that knows it
(docs/operations/deploys.md, enum values).
"""

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.conversation_engine import ReplyFailureKind
from app.schemas.dto.conversation_engine import GeneratedReply, PreparedTurn
from app.schemas.dto.spend_guard import SpendCheckRequest, SpendVerdict

type SpendCheck = UseCaseContract[SpendCheckRequest, SpendVerdict]


def check_turn_spend(
    check: SpendCheck | None, turn: PreparedTurn
) -> SpendVerdict | None:
    """The verdict for the turn; None when no guard is wired (tests, tools)."""

    if check is None:
        return None

    return check.run(
        SpendCheckRequest(
            business=turn.business,
            now=turn.received_at,
            model_id=turn.version.model_id,
        )
    )


def on_cheaper_model(turn: PreparedTurn, verdict: SpendVerdict | None) -> PreparedTurn:
    """The turn on the verdict's cheaper model, or as it is."""

    if verdict is None or verdict.cheaper_model_id is None:
        return turn

    if verdict.cheaper_model_id == turn.version.model_id:
        return turn

    return turn.model_copy(
        update={
            "version": turn.version.model_copy(
                update={"model_id": verdict.cheaper_model_id}
            )
        }
    )


def paused_reply(turn: PreparedTurn) -> GeneratedReply:
    """What the engine hands over when the hard limit holds the model back."""

    return GeneratedReply(
        failure=ReplyFailureKind.PROVIDER_ERROR,
        model_id=turn.version.model_id,
    )
