"""Profile saves, customer questions and a complete restaurant for the gap tests."""

from typed_time_provider import Microseconds

from app.schemas.constants.businesses import Weekday
from app.schemas.constants.profiles import ProfileGapKind
from app.schemas.domain.handoffs import UnansweredQuestionDocument
from app.schemas.domain.profiles import BusinessAddress, OpeningInterval
from app.schemas.dto.profiles.business_profile import (
    BookingRulesInput,
    ContactsInput,
    ProfileAnswerInput,
)
from app.schemas.dto.profiles.profile_gaps import ProfileGapsView
from app.schemas.dto.profiles.profile_steps import (
    BookingRulesStepInput,
    ContactsAndHoursStepInput,
    NicheAndLanguagesStepInput,
    ProfileStepInput,
    SaveProfileStepCommand,
)
from app.schemas.dto.resources import CreateResourceCommand, ResourceInput
from app.schemas.typings.bookings.constrained_integers import (
    PartySize,
    ResourceCapacity,
)
from app.schemas.typings.bookings.strings import ResourceName
from app.schemas.typings.businesses.constrained_integers import (
    ClosingMinuteOfDay,
    OpeningMinuteOfDay,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import AddressText
from app.schemas.typings.handoffs.constrained_integers import QuestionOccurrenceCount
from app.schemas.typings.handoffs.strings import UnansweredQuestionText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.profiles.constrained_strings import QuestionKey
from app.schemas.typings.profiles.strings import RawProfileAnswerText
from app.schemas.typings.users.prefixed_id import UserId
from tests.knowledge.harness import KnowledgeHarness


def kinds(view: ProfileGapsView) -> list[ProfileGapKind]:
    return [gap.kind for gap in view.gaps]


def save(
    harness: KnowledgeHarness,
    business_id: BusinessId,
    step_input: ProfileStepInput,
) -> None:
    harness.save_profile_step.run(
        SaveProfileStepCommand(
            business_id=business_id,
            actor_id=UserId(),
            step_input=step_input,
        )
    )


def add_question(
    harness: KnowledgeHarness,
    business_id: BusinessId,
    text: str,
    count: int,
    is_resolved: bool = False,
    is_sandbox: bool = False,
) -> None:
    harness.unanswered_question_repo.save(
        UnansweredQuestionDocument(
            business_id=business_id,
            question=UnansweredQuestionText(text),
            language=LanguageTag("ru"),
            occurrence_count=QuestionOccurrenceCount(count),
            last_seen_at=Microseconds(1_790_000_000_000_000),
            is_resolved=is_resolved,
            is_sandbox=is_sandbox,
        )
    )


def complete_restaurant(harness: KnowledgeHarness, business_id: BusinessId) -> None:
    save(
        harness,
        business_id,
        NicheAndLanguagesStepInput(
            answers=[
                ProfileAnswerInput(
                    question_key=QuestionKey("cuisine"),
                    answer=RawProfileAnswerText("Georgian"),
                )
            ]
        ),
    )
    save(
        harness,
        business_id,
        ContactsAndHoursStepInput(
            address=BusinessAddress(text=AddressText("Tbilisi, Rustaveli 1")),
            hours=[
                OpeningInterval(
                    weekday=Weekday.MONDAY,
                    opens_at=OpeningMinuteOfDay(720),
                    closes_at=ClosingMinuteOfDay(1380),
                )
            ],
            contacts=ContactsInput(
                handoff_phone_number=RawPhoneNumberInput("599123456")
            ),
        ),
    )
    save(
        harness,
        business_id,
        BookingRulesStepInput(
            booking_rules=BookingRulesInput(max_party_size=PartySize(12))
        ),
    )
    harness.create_resource.run(
        CreateResourceCommand(
            business_id=business_id,
            resource=ResourceInput(
                name=ResourceName("Table 1"),
                capacity=ResourceCapacity(4),
            ),
        )
    )
