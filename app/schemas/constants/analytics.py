from enum import StrEnum


class ProductEventName(StrEnum):
    """
    A step of an owner's way from sign-up to a paying customer, recorded in
    `product_events` (first-party analytics, no third-party tracker).

    Recorded by the server where the step happens: signing up and in,
    creating a business, a tunnel step skipped, a launch that went live or
    was stopped for the owner's attention, the agreement accepted, a channel
    connected, the milestones (test chat, live, first real conversation,
    booking and handoff), and the billing steps. The cabinet reports the
    tunnel steps an owner enters and completes (POST /v1/telemetry/events).
    """

    SIGNED_UP = "signed_up"
    SIGNED_IN = "signed_in"
    BUSINESS_CREATED = "business_created"
    TUNNEL_STEP_ENTERED = "tunnel_step_entered"
    TUNNEL_STEP_COMPLETED = "tunnel_step_completed"
    TUNNEL_STEP_SKIPPED = "tunnel_step_skipped"
    LAUNCH_SUCCEEDED = "launch_succeeded"
    LAUNCH_BLOCKED = "launch_blocked"
    DPA_ACCEPTED = "dpa_accepted"
    CHANNEL_CONNECTED = "channel_connected"
    TEST_CHAT_TRIED = "test_chat_tried"
    WENT_LIVE = "went_live"
    FIRST_REAL_CONVERSATION = "first_real_conversation"
    FIRST_BOOKING = "first_booking"
    FIRST_HANDOFF = "first_handoff"
    TRIAL_STARTED = "trial_started"
    SUBSCRIBED = "subscribed"
    PLAN_CHANGED = "plan_changed"
    CANCELLED = "cancelled"
    PAYMENT_FAILED = "payment_failed"


class ProductEventSource(StrEnum):
    """
    Who recorded a product event: the SERVER where the step happened, the
    CABINET (tunnel steps it reports), or the daily RECONCILIATION that
    derives a missing once-only step from the stored records (data from
    before analytics, demo data, an event whose write failed).
    """

    SERVER = "server"
    CABINET = "cabinet"
    RECONCILIATION = "reconciliation"


class TunnelStepKey(StrEnum):
    """
    A screen of the cabinet's "Create an AI assistant" tunnel, in order
    (web/src/lib/tunnel/steps.ts): what and where (before the business
    exists), the offer, hours, the people who take handoffs, channels,
    trying the assistant and the launch.
    """

    BUSINESS = "business"
    PLACE = "place"
    OFFER = "offer"
    HOURS = "hours"
    PEOPLE = "people"
    CHANNELS = "channels"
    TRY = "try"
    LAUNCH = "launch"


class TunnelStepAction(StrEnum):
    """What the cabinet reports about a tunnel step: entered or completed."""

    ENTERED = "entered"
    COMPLETED = "completed"


class TelemetryEventKind(StrEnum):
    """
    One entry of a telemetry batch: a Core Web Vital of a cabinet page
    (WEB_VITAL) or a tunnel step the owner entered or completed
    (TUNNEL_STEP).
    """

    WEB_VITAL = "web_vital"
    TUNNEL_STEP = "tunnel_step"


class WebVitalName(StrEnum):
    """
    A Core Web Vital: Largest Contentful Paint and Interaction to Next
    Paint in milliseconds, Cumulative Layout Shift in ten-thousandths.
    """

    LCP = "lcp"
    INP = "inp"
    CLS = "cls"


class DeviceClass(StrEnum):
    """The kind of screen a page was used on (by viewport width)."""

    MOBILE = "mobile"
    TABLET = "tablet"
    DESKTOP = "desktop"


class FunnelStep(StrEnum):
    """
    A step of the owners' funnel of a sign-up cohort, in order; an owner is
    counted at a step when they reached it and every step before it.
    """

    SIGNED_UP = "signed_up"
    BUSINESS_CREATED = "business_created"
    LAUNCH_ATTEMPTED = "launch_attempted"
    WENT_LIVE = "went_live"
    CHANNEL_CONNECTED = "channel_connected"
    FIRST_CONVERSATION = "first_conversation"
    PAID = "paid"


class MrrMovementKind(StrEnum):
    """
    How a business's monthly recurring revenue changed: NEW (first paid
    subscription), REACTIVATION (paying again after churning), EXPANSION
    (a dearer plan), CONTRACTION (a cheaper one) and CHURN (stopped paying).
    """

    NEW = "new"
    REACTIVATION = "reactivation"
    EXPANSION = "expansion"
    CONTRACTION = "contraction"
    CHURN = "churn"


class WebVitalRating(StrEnum):
    """
    Where a vital's 75th percentile stands against Google's thresholds:
    GOOD, NEEDS_IMPROVEMENT or POOR.
    """

    GOOD = "good"
    NEEDS_IMPROVEMENT = "needs_improvement"
    POOR = "poor"
