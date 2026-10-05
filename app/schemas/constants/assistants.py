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
    # The customer's own bookings still to come ("what time is my booking?").
    LIST_MY_BOOKINGS = "list_my_bookings"
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
    # The customer writes a language the business did not list.
    FOREIGN_LANGUAGE = "foreign_language"
    # The customer types a business language in Latin letters.
    TRANSLITERATED = "transliterated"
    # One of the owner's own checks (`AutotestCaseDocument`): the customer
    # asks its question word for word and the answer must meet its
    # expectation.
    OWNER_CHECK = "owner_check"


class JudgeCriterion(StrEnum):
    """The five things the judge scores (concept section 11)."""

    FACTS_AND_PRICES = "facts_and_prices"
    BOOKING_DATA = "booking_data"
    AI_DISCLOSURE = "ai_disclosure"
    HANDOFF = "handoff"
    LANGUAGE = "language"


class AutotestCheckCode(StrEnum):
    """
    Why the test harness failed a scenario, as a code each language renders:
    a deterministic check of what the assistant did (no booking, no handoff,
    records nobody asked for, a reply in another script, the AI disclosure
    in another language than the customer's), or why the
    scenario could not be evaluated at all.
    """

    NO_BOOKING_CREATED = "no_booking_created"
    NOT_HANDED_OFF = "not_handed_off"
    UNEXPECTED_RECORDS = "unexpected_records"
    WRONG_REPLY_LANGUAGE = "wrong_reply_language"
    WRONG_DISCLOSURE_LANGUAGE = "wrong_disclosure_language"
    # An owner check's expectation did not hold: the answer missed the
    # expected text, named the forbidden one, or made no request (lead).
    EXPECTED_TEXT_MISSING = "expected_text_missing"
    FORBIDDEN_TEXT_MENTIONED = "forbidden_text_mentioned"
    NO_LEAD_CREATED = "no_lead_created"
    CONVERSATION_FAILED = "conversation_failed"
    NO_CUSTOMER_MESSAGE = "no_customer_message"
    JUDGE_UNAVAILABLE = "judge_unavailable"
    JUDGE_UNREADABLE = "judge_unreadable"


class AutotestExpectation(StrEnum):
    """
    What an owner check demands of the assistant's answer to its question:
    to contain its expected text, never to contain it, to pass the
    conversation to a person, or to create a request (lead).
    """

    MUST_MENTION = "must_mention"
    MUST_NOT_MENTION = "must_not_mention"
    MUST_HAND_OFF = "must_hand_off"
    MUST_CREATE_LEAD = "must_create_lead"


class AutotestCaseSource(StrEnum):
    """
    Where an owner check came from: written by hand, saved from a corrected
    answer, from a question the assistant could not answer, or from a
    conversation rated bad.
    """

    OWNER = "owner"
    CORRECTION = "correction"
    UNANSWERED_QUESTION = "unanswered_question"
    BAD_RATING = "bad_rating"


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


class GoLiveCheckCode(StrEnum):
    """
    One launch condition of the go-live checklist (concept section 4,
    "Проверка"). The same codes name the reasons of a refused publish or
    rollback (`reasons[].code` of the 409), so clients branch on them
    instead of the English message.
    """

    SUBSCRIPTION_OR_TRIAL = "subscription_or_trial"
    DPA = "dpa"
    PROFILE_GAPS = "profile_gaps"
    STAFF_CONTACT = "staff_contact"
    AUTOTESTS = "autotests"
    VOICE_CONFIGURATION = "voice_configuration"


class AssistantVersionRefusalCode(StrEnum):
    """
    Why a version cannot be published or rolled back in its current state
    (besides the go-live checklist, whose "autotests" check covers versions
    that are untested or under test): `reasons[].code` of the 409 or 403.
    """

    VERSION_ALREADY_LIVE = "version_already_live"
    VERSION_ARCHIVED = "version_archived"
    VERSION_NOT_ARCHIVED = "version_not_archived"
    FORCE_PUBLISH_ADMIN_ONLY = "force_publish_admin_only"
