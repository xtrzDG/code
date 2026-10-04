"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class AutotestFailureCount(BaseConstrainedTypedInt):
    """Scenarios that failed or errored in the latest autotest run of a client."""

    ge = 0


class ClientCount(BaseConstrainedTypedInt):
    """Number of client businesses in a platform admin listing."""

    ge = 0


class HandoffCount(BaseConstrainedTypedInt):
    """Conversations passed to staff in a time window (sandbox excluded)."""

    ge = 0


class MeasuredReplyCount(BaseConstrainedTypedInt):
    """Assistant replies with a measured latency in a time window."""

    ge = 0


class OpenQuestionCount(BaseConstrainedTypedInt):
    """Unanswered customer questions not yet resolved by the owner."""

    ge = 0


class ReplyLatencyPercentileMilliseconds(BaseConstrainedTypedInt):
    """
    A percentile (p50, p95) of how long a client's customers waited for the
    assistant's replies in a time window, in milliseconds, read from
    latency buckets.
    """

    ge = 0


class ToolErrorCount(BaseConstrainedTypedInt):
    """Assistant tool calls that ended with an error in a time window."""

    ge = 0


# Keep abc order for all non example types, if possible.
