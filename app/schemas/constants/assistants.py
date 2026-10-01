from enum import StrEnum


class AssistantVersionStatus(StrEnum):
    """Lifecycle of an assistant version (concept: draft, testing, ready, published)."""

    DRAFT = "draft"
    TESTING = "testing"
    READY = "ready"
    TESTS_FAILED = "tests_failed"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class AssistantToolName(StrEnum):
    """Tool the language model may call (concept section 5)."""

    SEARCH_KNOWLEDGE = "search_knowledge"
    GET_PRICE = "get_price"
    CHECK_AVAILABILITY = "check_availability"
    CREATE_BOOKING = "create_booking"
    CANCEL_BOOKING = "cancel_booking"
    RESCHEDULE_BOOKING = "reschedule_booking"
    CREATE_LEAD = "create_lead"
    HANDOFF_TO_HUMAN = "handoff_to_human"
    SEND_LINK = "send_link"
    RECORD_UNANSWERED_QUESTION = "record_unanswered_question"


class AutotestRunStatus(StrEnum):
    """
    Progress of an autotest run: the worker plays it in the background
    (concept section 13, the job queue), so a run is RUNNING until it is
    FINISHED, or ERRORED when it could not be completed.
    """

    RUNNING = "running"
    FINISHED = "finished"
    ERRORED = "errored"


class AutotestScenarioKind(StrEnum):
    """Scripted test conversation run against every version (concept section 11)."""

    BOOKING = "booking"
    BOOKING_OUT_OF_HOURS = "booking_out_of_hours"
    CANCELLATION = "cancellation"
    PRICE_QUESTION = "price_question"
    UNKNOWN_QUESTION = "unknown_question"
    DISCOUNT_REQUEST = "discount_request"
    RUDE_CUSTOMER = "rude_customer"
    HUMAN_REQUEST = "human_request"
    PROMPT_INJECTION = "prompt_injection"
    EMERGENCY = "emergency"


class JudgeCriterion(StrEnum):
    """The five things the judge scores (concept section 11)."""

    FACTS_AND_PRICES = "facts_and_prices"
    BOOKING_DATA = "booking_data"
    AI_DISCLOSURE = "ai_disclosure"
    HANDOFF = "handoff"
    LANGUAGE = "language"


class AutotestOutcome(StrEnum):
    """Result of one autotest scenario."""

    PASSED = "passed"
    FAILED = "failed"
    ERRORED = "errored"


class LlmProvider(StrEnum):
    """Language-model provider behind the provider-neutral adapter."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    SCRIPTED = "scripted"


class LlmEffort(StrEnum):
    """Reasoning effort requested from the language model."""

    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
