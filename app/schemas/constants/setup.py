"""The guided launch: setup steps, starter answers, milestones and applying changes."""

from enum import StrEnum


class SetupStepCode(StrEnum):
    """
    One step of the guided setup, in the order the owner walks them: about
    the business, what it offers, hours and bookings, who receives handoffs,
    where customers write, trying the assistant, and going live. After the
    launch the guide goes on to the first real customer: writing to the
    assistant from the owner's own phone (PHONE_TEST), a second channel
    where customers write (SECOND_CHANNEL), and the link or QR code where
    customers see it (SHARE).

    The steps after the launch are new in this release: a skip of one is
    stored apart (`SetupStateDocument.skipped_after_launch`), which the
    release before ignores.
    """

    BUSINESS = "business"
    OFFER = "offer"
    HOURS_AND_BOOKINGS = "hours_and_bookings"
    STAFF_CONTACT = "staff_contact"
    CHANNELS = "channels"
    TEST = "test"
    LAUNCH = "launch"
    PHONE_TEST = "phone_test"
    SECOND_CHANNEL = "second_channel"
    SHARE = "share"


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
    The cabinet place where the owner acts; the cabinet maps it to a page:
    PROFILE (with a wizard step), STAFF_CONTACTS, CHANNELS,
    TEST_CHAT, AGREEMENT (the data processing agreement), BILLING,
    CHECKS (the automatic checks, under Advanced), APPLY_CHANGES, or
    OVERVIEW once everything is done; after the launch PHONE_TEST (the
    guide's QR code to write from a phone) and SHARE (the link and QR code
    for customers).
    """

    PROFILE = "profile"
    STAFF_CONTACTS = "staff_contacts"
    CHANNELS = "channels"
    TEST_CHAT = "test_chat"
    AGREEMENT = "agreement"
    BILLING = "billing"
    CHECKS = "checks"
    APPLY_CHANGES = "apply_changes"
    OVERVIEW = "overview"
    PHONE_TEST = "phone_test"
    SHARE = "share"


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
    live (first publish), the first real conversation, booking and handoff,
    and the first booking made while the business was closed.

    FIRST_AFTER_HOURS_BOOKING is new in this release, so it is kept in the
    setup state (`SetupStateDocument.after_hours_booking_at`) rather than
    in `activation_events`, which the release before reads.
    """

    TEST_CHAT_TRIED = "test_chat_tried"
    WENT_LIVE = "went_live"
    FIRST_CONVERSATION = "first_conversation"
    FIRST_BOOKING = "first_booking"
    FIRST_HANDOFF = "first_handoff"
    FIRST_AFTER_HOURS_BOOKING = "first_after_hours_booking"


class SetupShareMark(StrEnum):
    """
    How the owner put the assistant where customers find it, as the cabinet
    reports it: printed the QR card (PRINTED_QR) or saved the QR code as an
    image (DOWNLOADED_QR).
    """

    PRINTED_QR = "printed_qr"
    DOWNLOADED_QR = "downloaded_qr"


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
    payment, the version could not be built, the automatic checks found
    problems or stopped, voice could not be set up, or the version could
    not be published.
    """

    PROFILE_INCOMPLETE = "profile_incomplete"
    STAFF_CONTACT_MISSING = "staff_contact_missing"
    AGREEMENT_NOT_ACCEPTED = "agreement_not_accepted"
    PAYMENT_NEEDED = "payment_needed"
    BUILD_FAILED = "build_failed"
    CHECKS_FAILED = "checks_failed"
    CHECKS_STOPPED = "checks_stopped"
    VOICE_NOT_READY = "voice_not_ready"
    PUBLISH_FAILED = "publish_failed"


class PendingChangeArea(StrEnum):
    """
    The part of what the assistant knows that a change not live yet
    touches: PROFILE (name, kind, city, country, address, map, public
    phone, time zone), HOURS, SPECIAL_DAYS, ANSWERS (the niche questions),
    OFFER (menu items, services, rooms, packages, vehicles, products),
    QUESTIONS (frequent questions and policies), RESOURCES (what customers
    book), BOOKING_RULES, LINKS, LANGUAGES, CALLS (the phone line comes
    with the plan or goes), CONVERSATION (tone, what never to say, when
    to call a person) and OWNER_CHECKS (the owner's own checks written or
    changed since the version was last checked: the next apply asks them).
    """

    PROFILE = "profile"
    HOURS = "hours"
    SPECIAL_DAYS = "special_days"
    ANSWERS = "answers"
    OFFER = "offer"
    QUESTIONS = "questions"
    RESOURCES = "resources"
    BOOKING_RULES = "booking_rules"
    LINKS = "links"
    LANGUAGES = "languages"
    CALLS = "calls"
    CONVERSATION = "conversation"
    OWNER_CHECKS = "owner_checks"


class PendingChangeAction(StrEnum):
    """Whether something is new to the assistant, changed, or gone."""

    ADDED = "added"
    CHANGED = "changed"
    REMOVED = "removed"


class PendingChangeDetail(StrEnum):
    """
    What changed in a CHANGED offer item: its PRICE (the before and after
    prices are given), or other DETAILS (description, duration, tags).
    """

    PRICE = "price"
    DETAILS = "details"


class PendingChangeField(StrEnum):
    """
    The named fact a PROFILE, BOOKING_RULES or LANGUAGES change touches;
    the values are the fact table's own keys.
    """

    BUSINESS_NAME = "business_name"
    BUSINESS_TYPE = "business_type"
    CITY = "city"
    COUNTRY = "country"
    ADDRESS = "address"
    MAPS_LINK = "maps_link"
    PUBLIC_PHONE = "public_phone"
    TIME_ZONE = "time_zone"
    BOOKING_UNIT = "booking_unit"
    BOOKING_LENGTH = "booking_length"
    BOOKING_MAX_PARTY_SIZE = "booking_max_party_size"
    BOOKING_MIN_NOTICE = "booking_min_notice"
    BOOKING_DEPOSIT = "booking_deposit"
    BOOKING_CANCELLATION = "booking_cancellation"
    LANGUAGES = "languages"
    DEFAULT_LANGUAGE = "default_language"
