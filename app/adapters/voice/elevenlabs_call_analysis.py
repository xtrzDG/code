"""
The voice platform's evaluation of every call (ElevenLabs agent analysis):
the criteria and data collection fields the agent is set up with, and how
the post-call webhook's `analysis` is read back into a `CallAnalysis`.
"""

from collections.abc import Callable

from app.schemas.constants.calls import CallEvaluationResult
from app.schemas.domain.call_analysis import CallAnalysis
from app.schemas.typings.calls.constrained_integers import CallCollectedPartySize
from app.schemas.typings.calls.constrained_strings import (
    CallCollectedDate,
    CallCollectedTime,
)
from app.utilities.channels.json_values import (
    JsonObject,
    read_number,
    read_object,
    read_text,
)

BOOKING_CORRECT_CRITERION: str = "booking_correct"
DISCLOSURE_SAID_CRITERION: str = "disclosure_said"
BOOKING_DATE_FIELD: str = "booking_date"
BOOKING_TIME_FIELD: str = "booking_time"
PARTY_SIZE_FIELD: str = "party_size"
CALLBACK_REQUESTED_FIELD: str = "callback_requested"
# The goals the platform's evaluator judges every call by; the voice
# checks of autotests ask the same of a simulated call.
BOOKING_CORRECT_GOAL: str = (
    "Judge only a call in which the caller asked to book, move or cancel a "
    "booking. Success: the agent made (or changed) exactly the booking the "
    "caller asked for - the same date, time, number of people and name - "
    "and read it back to the caller before the call ended. Failure: any of "
    "these differs from what the caller asked, the agent said a booking was "
    "made when it was not, or it never read the booking back. Unknown: the "
    "caller asked for no booking."
)
DISCLOSURE_SAID_GOAL: str = (
    "Success: at the start of the call the agent said that it is an AI "
    "(virtual) assistant of the business. Failure: it never said so, or it "
    "said that it is a person."
)
EVALUATION_CRITERIA: tuple[tuple[str, str, str], ...] = (
    (BOOKING_CORRECT_CRITERION, "Booking matches the request", BOOKING_CORRECT_GOAL),
    (DISCLOSURE_SAID_CRITERION, "AI disclosure said", DISCLOSURE_SAID_GOAL),
)
DATA_COLLECTION: tuple[tuple[str, str, str], ...] = (
    (
        BOOKING_DATE_FIELD,
        "string",
        "The date of the booking the caller asked for, as YYYY-MM-DD. Empty "
        "when they asked for none.",
    ),
    (
        BOOKING_TIME_FIELD,
        "string",
        "The time of the booking the caller asked for, as HH:MM in 24 hours. "
        "Empty when they asked for none.",
    ),
    (
        PARTY_SIZE_FIELD,
        "integer",
        "How many people the booking the caller asked for is for.",
    ),
    (
        CALLBACK_REQUESTED_FIELD,
        "boolean",
        "True when the caller asked to be called back by a person.",
    ),
)
# The platform's words for a criterion's result.
EVALUATION_RESULTS: dict[str, CallEvaluationResult] = {
    "success": CallEvaluationResult.SUCCESS,
    "failure": CallEvaluationResult.FAILURE,
    "unknown": CallEvaluationResult.UNKNOWN,
}


def build_analysis_settings() -> JsonObject:
    """The agent's `platform_settings` parts that set up the evaluation."""

    return {
        "evaluation": {
            "criteria": [
                {
                    "id": criterion_id,
                    "name": name,
                    "type": "prompt",
                    "conversation_goal_prompt": goal,
                    "use_knowledge_base": False,
                }
                for criterion_id, name, goal in EVALUATION_CRITERIA
            ]
        },
        "data_collection": {
            field_id: {"type": value_type, "description": description}
            for field_id, value_type, description in DATA_COLLECTION
        },
    }


def read_call_analysis(data: JsonObject) -> CallAnalysis | None:
    """
    The evaluation of a post-call webhook's `data`; None when it carries
    none. Values the platform read in another shape than asked for (a
    date that is not YYYY-MM-DD) are left out.
    """

    analysis: JsonObject | None = read_object(data, "analysis")
    if analysis is None:
        return None

    criteria: JsonObject = read_object(analysis, "evaluation_criteria_results") or {}
    collected: JsonObject = read_object(analysis, "data_collection_results") or {}
    return CallAnalysis(
        booking_correct=read_result(criteria, BOOKING_CORRECT_CRITERION),
        disclosure_said=read_result(criteria, DISCLOSURE_SAID_CRITERION),
        booking_date=read_collected_date(collected),
        booking_time=read_collected_time(collected),
        party_size=read_party_size(collected),
        callback_requested=read_flag(collected, CALLBACK_REQUESTED_FIELD),
    )


def read_result(criteria: JsonObject, criterion_id: str) -> CallEvaluationResult | None:
    result: JsonObject = read_object(criteria, criterion_id) or {}
    return EVALUATION_RESULTS.get((read_text(result, "result") or "").lower())


def collected_field(collected: JsonObject, field_id: str) -> JsonObject:
    return read_object(collected, field_id) or {}


def read_flag(collected: JsonObject, field_id: str) -> bool | None:
    value: object = collected_field(collected, field_id).get("value")
    return value if isinstance(value, bool) else None


def read_typed_text[Typed: str](
    collected: JsonObject, field_id: str, typed: Callable[[str], Typed]
) -> Typed | None:
    """A text the platform read, in the shape `typed` asks; None otherwise."""

    value: str | None = read_text(collected_field(collected, field_id), "value")
    try:
        return None if value is None else typed(value.strip())
    except ValueError:
        return None


def read_collected_date(collected: JsonObject) -> CallCollectedDate | None:
    return read_typed_text(collected, BOOKING_DATE_FIELD, CallCollectedDate)


def read_collected_time(collected: JsonObject) -> CallCollectedTime | None:
    return read_typed_text(collected, BOOKING_TIME_FIELD, CallCollectedTime)


def read_party_size(collected: JsonObject) -> CallCollectedPartySize | None:
    """A whole number of people (2 or 2.0); None for anything else."""

    value: float | None = read_number(
        collected_field(collected, PARTY_SIZE_FIELD), "value"
    )
    if value is None or not float(value).is_integer():
        return None

    try:
        return CallCollectedPartySize(int(value))
    except ValueError:
        return None
