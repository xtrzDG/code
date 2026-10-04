"""Appending the turns of one reply to the stored transcript."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.conversation_repositories import (
    LlmTurnRepoContract,
)
from app.schemas.constants.conversations import LlmTurnRole
from app.schemas.domain.conversations import LlmTurnDocument
from app.schemas.dto.conversation_engine import PreparedTurn
from app.schemas.dto.conversations import LlmResponse
from app.schemas.typings.conversations.constrained_integers import (
    LlmTurnSequenceNumber,
)
from app.schemas.typings.conversations.strings import LlmProviderPayload
from app.use_cases.conversations.replies.turn_progress import TurnProgress
from app.utilities.conversations.canonical_turns import (
    build_canonical_assistant_payload,
)


def append_turn(
    llm_turn_repo: LlmTurnRepoContract,
    wall_clock: WallClock[Microseconds],
    turn: PreparedTurn,
    progress: TurnProgress,
    role: LlmTurnRole,
    payload: LlmProviderPayload,
    canonical_payload: LlmProviderPayload | None = None,
) -> None:
    """
    Store the next turn (only ever appended) and add it to both
    transcripts. `canonical_payload` is kept only when it differs from the
    payload (user and tool-result turns are canonical already).
    """

    stored_canonical: LlmProviderPayload | None = (
        None if canonical_payload == payload else canonical_payload
    )
    now: Microseconds = wall_clock.now_unix()
    llm_turn_repo.append(
        LlmTurnDocument(
            conversation_id=turn.conversation.id,
            sequence_number=LlmTurnSequenceNumber(progress.next_sequence_number),
            role=role,
            payload=payload,
            canonical_payload=stored_canonical,
            created_at=now,
            updated_at=now,
        )
    )
    progress.transcript.append(payload)
    progress.canonical_transcript.append(
        payload if stored_canonical is None else stored_canonical
    )
    progress.next_sequence_number += 1


def append_response(
    llm_turn_repo: LlmTurnRepoContract,
    wall_clock: WallClock[Microseconds],
    turn: PreparedTurn,
    progress: TurnProgress,
    response: LlmResponse,
) -> None:
    """The model's answer as returned, with its provider-neutral form."""

    append_turn(
        llm_turn_repo,
        wall_clock,
        turn,
        progress,
        LlmTurnRole.ASSISTANT,
        response.assistant_turn_payload,
        build_canonical_assistant_payload(response.text, response.tool_calls),
    )
