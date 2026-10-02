"""The guided launch: setup steps, starter answers, milestones and applying changes."""

from enum import StrEnum


class SetupStepCode(StrEnum):
    """
    One step of the guided setup, in the order the owner walks them: about
    the business, what it offers, hours and bookings, who receives handoffs,
    where customers write, trying the assistant, and going live.
    """

    BUSINESS = "business"
    OFFER = "offer"
    HOURS_AND_BOOKINGS = "hours_and_bookings"
    STAFF_CONTACT = "staff_contact"
    CHANNELS = "channels"
    TEST = "test"
    LAUNCH = "launch"


class SetupStepStatus(StrEnum):
    """
    Where a setup step stands: DONE, SKIPPED (an optional step the owner
    passed), NEXT (the first step still to do) or TODO (after the next one).
    """

    DONE = "done"
    SKIPPED = "skipped"
    NEXT = "next"
    TODO = "todo"


class SetupActionTarget(StrEnum):
    """
    The cabinet place that finishes a step; the cabinet maps it to a page
    (PROFILE with a wizard step, KNOWLEDGE, STAFF_CONTACTS, CHANNELS,
    TEST_CHAT, APPLY_CHANGES, or OVERVIEW once everything is done).
    """

    PROFILE = "profile"
    KNOWLEDGE = "knowledge"
    STAFF_CONTACTS = "staff_contacts"
    CHANNELS = "channels"
    TEST_CHAT = "test_chat"
    APPLY_CHANGES = "apply_changes"
    OVERVIEW = "overview"


class StarterSection(StrEnum):
    """
    A part of the profile the niche's starter answers can fill: opening
    hours, booking rules, the first bookable resource, handoff and
    forbidden rules, the tone and frequent questions with ready answers.
    Prices are never suggested; they come from the owner.
    """

    HOURS = "hours"
    BOOKING_RULES = "booking_rules"
    RESOURCE = "resource"
    HANDOFF_RULES = "handoff_rules"
    FORBIDDEN_RULES = "forbidden_rules"
    TONE = "tone"
    FAQ = "faq"


class StarterSectionState(StrEnum):
    """
    SUGGESTED: the section is empty and applying the starter answers fills
    it. ALREADY_SET: the owner has filled it; applying leaves it as it is.
    """

    SUGGESTED = "suggested"
    ALREADY_SET = "already_set"


class ActivationEventKind(StrEnum):
    """
    A milestone on the way from sign-up to the first customers, recorded
    once per business: the owner tried the test chat, the assistant went
    live (first publish), the first real conversation, booking and handoff.
    """

    TEST_CHAT_TRIED = "test_chat_tried"
    WENT_LIVE = "went_live"
    FIRST_CONVERSATION = "first_conversation"
    FIRST_BOOKING = "first_booking"
    FIRST_HANDOFF = "first_handoff"


class ApplyChangesStage(StrEnum):
    """
    Progress of "Apply changes": BUILDING the new version from the profile
    and knowledge, CHECKING it with the automatic checks, PUBLISHING it,
    LIVE once customers get it, or NEEDS_ATTENTION with the reasons.
    """

    BUILDING = "building"
    CHECKING = "checking"
    PUBLISHING = "publishing"
    LIVE = "live"
    NEEDS_ATTENTION = "needs_attention"


class ApplyAttentionCode(StrEnum):
    """
    Why applied changes did not go live, in words an owner can act on:
    something required is missing in the profile, nobody receives
    handoffs, the data processing agreement is not accepted, the plan needs
    payment, the automatic checks found problems or stopped, voice could
    not be set up, or the version could not be published.
    """

    PROFILE_INCOMPLETE = "profile_incomplete"
    STAFF_CONTACT_MISSING = "staff_contact_missing"
    AGREEMENT_NOT_ACCEPTED = "agreement_not_accepted"
    PAYMENT_NEEDED = "payment_needed"
    CHECKS_FAILED = "checks_failed"
    CHECKS_STOPPED = "checks_stopped"
    VOICE_NOT_READY = "voice_not_ready"
    PUBLISH_FAILED = "publish_failed"
