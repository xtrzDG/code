"""Short calls of "Fix this answer" over a teaching world."""

from typing import Any

from app.schemas.constants.knowledge import AnswerCorrectionScope
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.conversation_feed.answer_corrections import (
    AnswerCorrectionDraft,
    AnswerCorrectionQuery,
    AnswerCorrectionRequest,
    AnswerCorrectionResult,
    CorrectAnswerCommand,
)
from app.schemas.typings.users.prefixed_id import UserId
from tests.teaching.teaching_world import TeachingWorld


def open_draft(
    world: TeachingWorld,
    answer: MessageDocument,
    user_id: UserId | None = None,
) -> AnswerCorrectionDraft:
    return world.draft.run(
        AnswerCorrectionQuery(
            user_id=user_id or world.brain.owner_id,
            business_id=world.brain.business.id,
            conversation_id=answer.conversation_id,
            message_id=answer.id,
        )
    )


def fix(
    world: TeachingWorld,
    answer: MessageDocument,
    scope: AnswerCorrectionScope,
    user_id: UserId | None = None,
    **fields: Any,
) -> AnswerCorrectionResult:
    world.advance(60)
    return world.correct.run(
        CorrectAnswerCommand(
            user_id=user_id or world.brain.owner_id,
            business_id=world.brain.business.id,
            conversation_id=answer.conversation_id,
            message_id=answer.id,
            request=AnswerCorrectionRequest.model_validate({"scope": scope, **fields}),
        )
    )
