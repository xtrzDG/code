from enum import StrEnum


class EvalCriterion(StrEnum):
    """
    A deterministic criterion of the evaluation harness (scripts/run_evals.py):
    each scenario reply is checked by code, not by a model.

    - LANGUAGE: every reply is in the scenario's language and script.
    - DISCLOSURE: the AI disclosure appears exactly once, in that language.
    - TOOL_CALLS: the expected tools were called and forbidden ones were not.
    - BOOKING_FIELDS: booking and lead calls carry the persona's details.
    - PRICES: the expected price of the price list is named.
    - REQUIRED_FACTS: the expected facts (hours, numbers, words) are named.
    - FORBIDDEN_VALUES: no forbidden value (a promised discount, a piece of
      the instruction) is written.
    - HANDOFF: the conversation went to a person exactly when it should.
    - GUARD: the invented-numbers guard did not have to step in.
    - RECORDS: the autotest checks of what was created (bookings, leads).
    """

    LANGUAGE = "language"
    DISCLOSURE = "disclosure"
    TOOL_CALLS = "tool_calls"
    BOOKING_FIELDS = "booking_fields"
    PRICES = "prices"
    REQUIRED_FACTS = "required_facts"
    FORBIDDEN_VALUES = "forbidden_values"
    HANDOFF = "handoff"
    GUARD = "guard"
    RECORDS = "records"
