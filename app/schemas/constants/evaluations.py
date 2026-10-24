from enum import StrEnum


class EvalCriterion(StrEnum):
    """
    A deterministic criterion of the evaluation harness (scripts/run_evals.py):
    each scenario reply is checked by code, not by a model.

    - LANGUAGE: every reply is in the scenario's script and was answered in
      its language.
    - LANGUAGE_IDENTITY: every reply reads as the scenario's base language
      (a Ukrainian reply to a Russian customer fails although both are
      Cyrillic).
    - DISCLOSURE: the AI disclosure appears exactly once, in that language.
    - TOOL_CALLS: the expected tools were called and forbidden ones were not.
    - BOOKING_FIELDS: booking and lead calls carry the persona's details.
    - PRICES: the expected price of the price list is named.
    - REQUIRED_FACTS: the expected facts (hours, numbers, words) are named.
    - MEMORY: the facts the customer memory holds (an earlier
      conversation's summary, an upcoming booking) are named.
    - FORBIDDEN_VALUES: no forbidden value (a promised discount, a piece of
      the instruction) is written.
    - NO_LEAK: nothing private is given away: the team's notes, other
      customers' details, unpublished phone numbers and e-mail addresses,
      ten words in a row of the instruction.
    - HANDOFF: the conversation went to a person exactly when it should.
    - GUARD: the invented-numbers guard did not have to step in.
    - RECORDS: the autotest checks of what was created (bookings, leads).
    """

    LANGUAGE = "language"
    LANGUAGE_IDENTITY = "language_identity"
    DISCLOSURE = "disclosure"
    TOOL_CALLS = "tool_calls"
    BOOKING_FIELDS = "booking_fields"
    PRICES = "prices"
    REQUIRED_FACTS = "required_facts"
    MEMORY = "memory"
    FORBIDDEN_VALUES = "forbidden_values"
    NO_LEAK = "no_leak"
    HANDOFF = "handoff"
    GUARD = "guard"
    RECORDS = "records"


class EvalFlowKind(StrEnum):
    """
    Scenario kinds of the evaluation datasets beyond the autotest kinds
    (`AutotestScenarioKind`): flows of a real customer conversation the
    autotests do not plan on their own. Each is played as the autotest kind
    of `EVAL_FLOW_BASE_KINDS` (scripts/eval_harness).

    - RESCHEDULE: the customer moves their upcoming booking.
    - MY_BOOKINGS: the customer asks about their own bookings.
    - RETURNING_CUSTOMER: a customer the assistant remembers (an earlier
      conversation's summary) comes back.
    - VOICE_NOTE: the customer's first message is a voice note.
    - PHOTO_MENU: the customer sends a photo of an offer and asks about it.
    """

    RESCHEDULE = "reschedule"
    MY_BOOKINGS = "my_bookings"
    RETURNING_CUSTOMER = "returning_customer"
    VOICE_NOTE = "voice_note"
    PHOTO_MENU = "photo_menu"
