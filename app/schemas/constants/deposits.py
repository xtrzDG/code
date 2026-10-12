from enum import StrEnum


class DepositRule(StrEnum):
    """
    How a deposit policy counts the amount: a fixed sum for the booking
    (FIXED), a fixed sum for each guest (PER_GUEST), or a percent of the
    booking's value (PERCENT_OF_VALUE; a booking without a known value asks
    none).
    """

    FIXED = "fixed"
    PER_GUEST = "per_guest"
    PERCENT_OF_VALUE = "percent_of_value"


class DepositTarget(StrEnum):
    """
    What a deposit policy applies to: a bookable place (RESOURCE: a table, a
    room, a master), a service or package (SERVICE: its policy wins over the
    place's), or the banquet requests the assistant takes (BANQUET).
    """

    RESOURCE = "resource"
    SERVICE = "service"
    BANQUET = "banquet"


class DepositStatus(StrEnum):
    """
    Lifecycle of one deposit request.

    AWAITING: the link went to the customer; a booking keeps its place until
    the hold ends. PAID: staff marked it paid (the merchant's own account is
    the proof). EXPIRED: the hold ended unpaid and the booking was released.
    CANCELLED: the booking or request ended before anything was paid.
    REFUND_DUE: a paid booking was cancelled in time under the policy; staff
    return the money in their merchant account. KEPT: a paid booking was
    cancelled too late or the guest did not come; the deposit stays.
    """

    AWAITING = "awaiting"
    PAID = "paid"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    REFUND_DUE = "refund_due"
    KEPT = "kept"


class PaymentLinkKind(StrEnum):
    """
    An owner's payment page: one fixed address that charges one amount
    (STATIC, named by the policies it fits), or an address template the
    platform fills with the amount and the reference (TEMPLATE).
    """

    STATIC = "static"
    TEMPLATE = "template"


class DepositSubject(StrEnum):
    """What a deposit request secures: a booking or a banquet request."""

    BOOKING = "booking"
    BANQUET = "banquet"


class DepositRefusalCode(StrEnum):
    """
    Why a deposit could not be asked or changed, as the `reasons[].code` of
    the error, so the cabinet and the assistant explain it.
    """

    # The business takes no deposits, or has no payment page for this one.
    DEPOSITS_OFF = "deposits_off"
    NO_PAYMENT_LINK = "no_payment_link"
    # The payment page is not an https address the platform accepts.
    LINK_NOT_HTTPS = "link_not_https"
    LINK_INVALID = "link_invalid"
    # A template names a placeholder the platform does not fill, or none.
    TEMPLATE_INVALID = "template_invalid"
    # The policy's currency is not the business's.
    CURRENCY_MISMATCH = "currency_mismatch"
    # The deposit already moved on (paid, released, refunded).
    STATUS_CHANGED = "status_changed"


class DepositNoticeKind(StrEnum):
    """
    A message the business sends about a waiting deposit: the reminder
    while the place is still held (REMINDER), and the word that the place
    was let go when the hold ran out unpaid (RELEASED).
    """

    REMINDER = "reminder"
    RELEASED = "released"


class PaymentLinkOutcome(StrEnum):
    """
    What send_payment_link did: sent the payment line (SENT; a deposit
    already waiting is sent again as it is), found that no deposit applies
    to this booking or request (NOT_REQUIRED, with the reason), or that it
    is paid already (ALREADY_PAID).
    """

    SENT = "sent"
    NOT_REQUIRED = "not_required"
    ALREADY_PAID = "already_paid"


class DepositExemption(StrEnum):
    """Why no deposit is asked of a booking or a banquet request."""

    DEPOSITS_OFF = "deposits_off"
    NO_POLICY = "no_policy"
    SMALL_PARTY = "small_party"
    VALUE_UNKNOWN = "value_unknown"
    NOT_A_BANQUET = "not_a_banquet"
    NOTHING_OPEN = "nothing_open"
