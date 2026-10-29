"""
Which worker processes stopped beating. A worker writes its pulse on every
tick of its periodic thread (well under a minute), so a pulse older than
WORKER_PULSE_STALE_SECONDS (the readiness check's own limit) means the
process died or hung; the system page marks it.

The alert is stricter about what it calls a stuck worker:

- the pulse is older than WORKER_PULSE_ALERT_SECONDS: a tick that ran a
  slow periodic job (the alerts job itself runs before its worker beats)
  is no fault, a periodic thread blocked for that long is;
- it is not the freshest pulse: the alerts job runs in a worker, so the
  freshest one is alive (with one worker, the job cannot page about it);
- it was not replaced: a deploy starts workers of a new release (only
  pulses of the release the freshest pulse names count), and a restart
  starts a new process after the old one went silent (a silent pulse
  counts only while no live worker started after its last beat).

What stays is a worker that hung or crashed for good while the others ran
on, which pages until a worker replaces it or its pulse is purged a day
later.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.schemas.domain.jobs import WorkerHeartbeatDocument

MICROSECONDS_PER_SECOND: int = 1_000_000
WORKER_PULSE_STALE_SECONDS: int = 5 * 60
WORKER_PULSE_ALERT_SECONDS: int = 2 * WORKER_PULSE_STALE_SECONDS


def pulse_age_seconds(pulse: WorkerHeartbeatDocument, now: Microseconds) -> int:
    """Whole seconds since the worker last beat (never negative)."""

    return max(0, (int(now) - int(pulse.beat_at)) // MICROSECONDS_PER_SECOND)


def is_pulse_stale(pulse: WorkerHeartbeatDocument, now: Microseconds) -> bool:
    """The worker has not beaten for longer than the readiness check allows."""

    return pulse_age_seconds(pulse, now) > WORKER_PULSE_STALE_SECONDS


def find_stale_workers(
    pulses: Sequence[WorkerHeartbeatDocument],
    now: Microseconds,
) -> list[WorkerHeartbeatDocument]:
    """The stuck workers of the current release, the longest silent first."""

    if not pulses:
        return []

    freshest: WorkerHeartbeatDocument = max(
        pulses, key=lambda pulse: int(pulse.beat_at)
    )
    live_starts: list[int] = [
        int(pulse.started_at) for pulse in pulses if not is_pulse_silent(pulse, now)
    ]
    stale: list[WorkerHeartbeatDocument] = [
        pulse
        for pulse in pulses
        if pulse.id != freshest.id
        and pulse.release == freshest.release
        and is_pulse_silent(pulse, now)
        and not any(started >= int(pulse.beat_at) for started in live_starts)
    ]
    return sorted(stale, key=lambda pulse: int(pulse.beat_at))


def is_pulse_silent(pulse: WorkerHeartbeatDocument, now: Microseconds) -> bool:
    """Silent for longer than the alert allows (a stuck periodic thread)."""

    return pulse_age_seconds(pulse, now) > WORKER_PULSE_ALERT_SECONDS
