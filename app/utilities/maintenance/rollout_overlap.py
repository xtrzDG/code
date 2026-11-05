"""
Whether the release overlap of a deploy is over, read from the worker
pulses (`worker_heartbeats`): during a deploy the previous release's
workers (and API instances) serve next to the new ones, and after a
rollback the other way round. Post-deploy data tasks rewrite rows only
once no worker of another release has beaten for a while, so no process
that would write the old shape again is left.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.schemas.domain.jobs import WorkerHeartbeatDocument
from app.schemas.dto.data_tasks import RolloutView
from app.schemas.typings.platform.constrained_strings import ReleaseVersion

MICROSECONDS_PER_SECOND: int = 1_000_000
# A worker of another release that beat within this long may still run (a
# slow shutdown, an API instance draining behind it): longer than Render's
# deploy overlap, the 30 and 60 second shutdown delays and the 5 minutes a
# pulse counts as fresh.
ROLLOUT_SETTLE_SECONDS: int = 15 * 60


def rollout_window_start(now: Microseconds) -> Microseconds:
    """Pulses before this no longer keep the overlap open."""

    return Microseconds(int(now) - ROLLOUT_SETTLE_SECONDS * MICROSECONDS_PER_SECOND)


def read_rollout(
    pulses: Sequence[WorkerHeartbeatDocument],
    release: ReleaseVersion | None,
    now: Microseconds,
) -> RolloutView:
    """
    Settled when no pulse of the settling window names another release
    than `release` (an unnamed release, as in development, is a release of
    its own: equal only to another unnamed one).
    """

    window_start: int = int(rollout_window_start(now))
    others: list[WorkerHeartbeatDocument] = [
        pulse
        for pulse in pulses
        if int(pulse.beat_at) >= window_start and pulse.release != release
    ]
    if not others:
        return RolloutView(is_settled=True, release=release)

    return RolloutView(
        is_settled=False,
        release=release,
        other_releases=sorted(
            {pulse.release for pulse in others if pulse.release is not None},
            key=str,
        ),
        settles_at=Microseconds(
            max(int(pulse.beat_at) for pulse in others)
            + ROLLOUT_SETTLE_SECONDS * MICROSECONDS_PER_SECOND
        ),
    )
