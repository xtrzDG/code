"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class CancellationCount(BaseConstrainedTypedInt):
    """How many cancellations (of one reason, or in all) a period had."""

    ge = 0


class ConversationsSinceCancellation(BaseConstrainedTypedInt):
    """
    How many customer conversations a business's assistant started since
    the owner cancelled (it keeps taking requests): the heart of the
    win-back message.
    """

    ge = 0


class PauseMonthCount(BaseConstrainedTypedInt):
    """
    How many whole months one seasonal pause lasts: one to four, the most
    a business may pause in any twelve months.

    Example:
        winter = PauseMonthCount(3)
    """

    ge = 1
    le = 4


class PauseMonthsAllowed(BaseConstrainedTypedInt):
    """
    How many months a business may still pause now, within the cap of the
    twelve-month window (0 when the cap is used up).
    """

    ge = 0
    le = 12


class PausePricePercent(BaseConstrainedTypedInt):
    """
    The share of the plan's monthly price a paused month costs (the
    business keeps its channels and the assistant takes requests).

    Example:
        pause_price = PausePricePercent(15)
    """

    ge = 1
    le = 100


class PauseWindowMonths(BaseConstrainedTypedInt):
    """The rolling window the pause cap counts months in (twelve)."""

    ge = 1
    le = 24


class PausedMonthCount(BaseConstrainedTypedInt):
    """How many months a business already paused within the window."""

    ge = 0


class SaveCreditPercent(BaseConstrainedTypedInt):
    """
    The one-time credit offered to an owner about to cancel, as a share of
    one month of their plan.

    Example:
        half_a_month = SaveCreditPercent(50)
    """

    ge = 1
    le = 100


class SubscriptionStepCount(BaseConstrainedTypedInt):
    """
    How many lifecycle steps of one kind a period had: offers accepted,
    pauses scheduled, pauses ended, win-back messages sent, owners back.
    """

    ge = 0


class WinBackDayOffset(BaseConstrainedTypedInt):
    """
    Days after a cancellation a win-back message goes out (14 and 30).

    Example:
        first_message = WinBackDayOffset(14)
    """

    ge = 1
    le = 365


class WinBackRecipientCount(BaseConstrainedTypedInt):
    """How many addresses one win-back message was queued for."""

    ge = 0


# Keep abc order for all non example types, if possible.
