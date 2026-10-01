from enum import StrEnum


class AssistantVersionStatus(StrEnum):
    """Lifecycle of one assembled assistant version."""

    ASSEMBLED = "assembled"
    TESTS_PASSED = "tests_passed"
    TESTS_FAILED = "tests_failed"
    ACTIVE = "active"
    RETIRED = "retired"


class AssistantSkill(StrEnum):
    """Capability shared by every niche template."""

    ANSWER_FROM_FACTS = "answer_from_facts"
    CHECK_AVAILABILITY = "check_availability"
    CREATE_BOOKING = "create_booking"
    CREATE_LEAD = "create_lead"
    HANDOFF_TO_HUMAN = "handoff_to_human"
    REMINDER = "reminder"
    PAYMENT_LINK = "payment_link"


class AssistantToolName(StrEnum):
    """Tool the language model may call during a conversation."""

    CHECK_AVAILABILITY = "check_availability"
    CREATE_BOOKING = "create_booking"
    CANCEL_BOOKING = "cancel_booking"
    CREATE_LEAD = "create_lead"
    HANDOFF_TO_HUMAN = "handoff_to_human"
    RECORD_UNANSWERED_QUESTION = "record_unanswered_question"


class AutotestScenarioKind(StrEnum):
    """Scripted test conversation run against every assembled version."""

    BOOKING = "booking"
    CANCELLATION = "cancellation"
    PRICE_QUESTION = "price_question"
    UNKNOWN_QUESTION = "unknown_question"
    RUDE_CUSTOMER = "rude_customer"
    HUMAN_REQUEST = "human_request"
    EMERGENCY = "emergency"


class AutotestOutcome(StrEnum):
    """Result of one autotest scenario."""

    PASSED = "passed"
    FAILED = "failed"
    ERRORED = "errored"


class LlmEffort(StrEnum):
    """Reasoning effort requested from the language model."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"
    MAX = "max"
