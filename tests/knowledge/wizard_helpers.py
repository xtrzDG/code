"""Profile wizard answers, choices, hours and a one-step save, for the wizard tests."""

from app.schemas.constants.businesses import Weekday
from app.schemas.domain.profiles import OpeningInterval
from app.schemas.dto.profiles.business_profile import ProfileAnswerInput
from app.schemas.dto.profiles.profile_steps import (
    ProfileStepInput,
    ProfileStepSaveResult,
    SaveProfileStepCommand,
)
from app.schemas.typings.businesses.constrained_integers import (
    ClosingMinuteOfDay,
    OpeningMinuteOfDay,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.profiles.constrained_strings import (
    QuestionChoiceKey,
    QuestionKey,
)
from app.schemas.typings.profiles.strings import RawProfileAnswerText
from app.schemas.typings.users.prefixed_id import UserId
from tests.knowledge.harness import KnowledgeHarness


def answer(key: str, text: str) -> ProfileAnswerInput:
    return ProfileAnswerInput(
        question_key=QuestionKey(key), answer=RawProfileAnswerText(text)
    )


def choices(key: str, *choice_keys: str) -> ProfileAnswerInput:
    return ProfileAnswerInput(
        question_key=QuestionKey(key),
        choice_keys=[QuestionChoiceKey(choice_key) for choice_key in choice_keys],
    )


def hours(weekday: Weekday, opens: int, closes: int) -> OpeningInterval:
    return OpeningInterval(
        weekday=weekday,
        opens_at=OpeningMinuteOfDay(opens),
        closes_at=ClosingMinuteOfDay(closes),
    )


def save_step(
    harness: KnowledgeHarness,
    business_id: BusinessId,
    step_input: ProfileStepInput,
    actor_id: UserId | None = None,
) -> ProfileStepSaveResult:
    return harness.save_profile_step.run(
        SaveProfileStepCommand(
            business_id=business_id,
            actor_id=actor_id or UserId(),
            step_input=step_input,
        )
    )
