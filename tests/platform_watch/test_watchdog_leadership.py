"""
One API process leads the pipeline watchdog: the lease in its mark is read
and renewed under the alert-state lock, so of two processes looking at the
same moment exactly one leads and the team hears the news once; another
process takes over only after the leader's lease ran out.
"""

import threading
import time

from app.repositories.platform_monitor_repository import PlatformMonitorRepository
from app.schemas.constants.monitoring import PlatformMonitor
from app.schemas.constants.observability import PipelineState
from app.schemas.domain.platform_monitors import PlatformMonitorDocument
from app.schemas.dto.pipeline_health import PipelineWatchReport, PipelineWatchTick
from app.schemas.typings.monitoring.constrained_integers import (
    PipelineWatchdogSeconds,
)
from app.use_cases.admin.alerts.watchdog_lease import may_lead, renewed_lease
from tests.platform_ops.ops_documents import NOW, SECOND, at, pulse
from tests.platform_watch.watch_world import API_ONE, API_TWO, WatchWorld

TICK: PipelineWatchTick = PipelineWatchTick()


def test_the_first_look_leads_and_renews_its_lease() -> None:
    world = WatchWorld()
    world.worker_beats()

    report = world.watchdog(API_ONE).run(TICK)

    mark = world.monitor_repo.get(PlatformMonitor.PIPELINE_WATCHDOG)
    assert report == PipelineWatchReport(is_leader=True, pipeline=PipelineState.FLOWING)
    assert mark is not None and mark.holder == API_ONE
    assert int(mark.checked_at) == int(NOW)
    assert mark.lease_until == at(150 * SECOND)


def test_another_process_waits_while_the_lease_runs() -> None:
    world = WatchWorld()
    world.worker_beats()
    world.watchdog(API_ONE).run(TICK)

    world.clock.advance(149 * SECOND)
    follower = world.watchdog(API_TWO).run(TICK)
    leader = world.watchdog(API_ONE).run(TICK)

    assert follower == PipelineWatchReport()
    assert leader.is_leader
    mark = world.monitor_repo.get(PlatformMonitor.PIPELINE_WATCHDOG)
    assert mark is not None and mark.holder == API_ONE


def test_another_process_takes_over_a_lapsed_lease() -> None:
    world = WatchWorld()
    world.worker_beats()
    world.watchdog(API_ONE).run(TICK)

    world.clock.advance(150 * SECOND)
    world.worker_beats()
    taken = world.watchdog(API_TWO).run(TICK)
    former = world.watchdog(API_ONE).run(TICK)

    assert taken.is_leader and not former.is_leader
    mark = world.monitor_repo.get(PlatformMonitor.PIPELINE_WATCHDOG)
    assert mark is not None and mark.holder == API_TWO


def test_the_lease_rule() -> None:
    interval = PipelineWatchdogSeconds(60)
    held = renewed_lease(None, API_ONE, interval, None, NOW)
    released = held.model_copy(update={"holder": None})
    open_ended = held.model_copy(update={"lease_until": None})

    assert may_lead(None, API_TWO, NOW)
    assert may_lead(held, API_ONE, NOW)
    assert not may_lead(held, API_TWO, at(149 * SECOND))
    assert may_lead(held, API_TWO, at(150 * SECOND))
    assert may_lead(released, API_TWO, NOW)
    assert may_lead(open_ended, API_TWO, NOW)
    renewed = renewed_lease(held, API_TWO, interval, None, at(SECOND))
    assert renewed.created_at == held.created_at
    assert renewed.updated_at == at(SECOND)


class SlowMonitorRepo(PlatformMonitorRepository):
    """Reads the watchdog's mark slowly and records how many read at once."""

    def __init__(self, repo: PlatformMonitorRepository) -> None:
        self._repo: PlatformMonitorRepository = repo
        self._guard = threading.Lock()
        self._inside: int = 0
        self.most_inside: int = 0

    def get(self, monitor: PlatformMonitor) -> PlatformMonitorDocument | None:
        with self._guard:
            self._inside += 1
            self.most_inside = max(self.most_inside, self._inside)
        try:
            time.sleep(0.05)
            return self._repo.get(monitor)
        finally:
            with self._guard:
                self._inside -= 1

    def save(self, mark: PlatformMonitorDocument) -> None:
        self._repo.save(mark)


def test_two_processes_looking_at_once_elect_one_leader_and_alert_once() -> None:
    world = WatchWorld()
    slow = SlowMonitorRepo(world.monitor_repo)
    world.monitor_repo = slow
    # The only worker pulsed ten minutes ago: whoever leads alerts.
    stale = pulse("srv-worker-1", at(-600 * SECOND))
    world.pulses.upsert(str(stale.id), stale)
    watchdogs = [world.watchdog(API_ONE), world.watchdog(API_TWO)]
    start = threading.Barrier(len(watchdogs))
    reports: list[PipelineWatchReport] = []
    reports_guard = threading.Lock()

    def look(index: int) -> None:
        start.wait(timeout=5)
        report = watchdogs[index].run(TICK)
        with reports_guard:
            reports.append(report)

    threads = [
        threading.Thread(target=look, args=(index,)) for index in range(len(watchdogs))
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    leaders = [report for report in reports if report.is_leader]
    assert len(reports) == 2
    assert len(leaders) == 1
    assert leaders[0].pipeline is PipelineState.STALLED
    assert slow.most_inside == 1
    assert world.sender.headlines() == [
        "[SEV1] FIRING: No worker answers",
        "[SEV1] FIRING: No worker answers",
    ]
