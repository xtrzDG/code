"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class AlertCooldownMinutes(BaseConstrainedTypedInt):
    """
    How long a firing platform alert stays quiet after it was sent
    (PLATFORM_ALERT_COOLDOWN_MINUTES): it is sent again only when it still
    fires after that long.
    """

    ge = 5
    le = 1440


class AlertFigure(BaseConstrainedTypedInt):
    """
    What a platform alert measured in its last check, in the unit of its
    rule: a count of jobs, messages or trips, an age in seconds, or a
    percentage.
    """

    ge = 0


class AlertThreshold(BaseConstrainedTypedInt):
    """
    The figure above which a platform alert fires, in the unit of its rule
    (ops/alerts/*.yaml): 0 for "any at all".
    """

    ge = 0


class AlertVolumeFloor(BaseConstrainedTypedInt):
    """
    The fewest events a rate alert needs in its window before its rate
    means anything (3 failed model calls of 4 is not an outage).
    """

    ge = 0


class AlertWindowMinutes(BaseConstrainedTypedInt):
    """The stretch of time a platform alert's figure is measured over."""

    ge = 1
    le = 7 * 24 * 60


class ArchivedRowCount(BaseConstrainedTypedInt):
    """
    How many rows a backup archive holds across every table (the dump's
    row counts added up), as the system page shows a backup or drill.
    """

    ge = 0


class ChannelIssueCount(BaseConstrainedTypedInt):
    """How many connected channels are in ERROR across the platform."""

    ge = 0


class CollectionRowEstimate(BaseConstrainedTypedInt):
    """
    About how many rows a database table holds (the planner's estimate
    from its statistics, no count of the table).
    """

    ge = 0


class LaneJobCount(BaseConstrainedTypedInt):
    """How many queued jobs of one lane are in one state right now."""

    ge = 0


class NotificationCount(BaseConstrainedTypedInt):
    """How many times one platform alert episode was sent to the team."""

    ge = 0


class PipelineWatchdogSeconds(BaseConstrainedTypedInt):
    """
    How often the API's pipeline watchdog looks at the workers
    (PIPELINE_WATCHDOG_SECONDS): 0 switches it off.
    """

    ge = 0
    le = 3600


class SignalEventCount(BaseConstrainedTypedInt):
    """
    How many platform signal events (model calls, failed model calls,
    refused login codes) were counted in one window.
    """

    ge = 0


class StorageByteSize(BaseConstrainedTypedInt):
    """
    The disk space a table takes with its indexes and its overflow storage,
    or the whole database, in bytes.
    """

    ge = 0


class WaitSeconds(BaseConstrainedTypedInt):
    """How long the oldest due job of a lane has been waiting for a worker."""

    ge = 0


class WorkerPulseAgeSeconds(BaseConstrainedTypedInt):
    """How long ago one background worker process last wrote its pulse."""

    ge = 0


# Keep abc order for all non example types, if possible.
