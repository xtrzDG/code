# Missed periodic job runs

**Alert:** `missed_job_runs` (SEV2): a shared periodic job of the current
release has not succeeded within its interval plus its grace (a quarter of
the interval, at least 30 minutes). It does not depend on Sentry Crons:
every worker registers the periodic jobs it knows when it starts and
writes a job's heartbeat after each successful run
(`periodic_job_heartbeats`); the platform alerts job reads the overdue
ones every five minutes. The message names each job, its lane and how
long ago it last succeeded.

## Check

1. Admin → System: are the workers beating (`stale_worker`,
   `worker_down`)? A whole worker down is [worker-down](worker-down.md).
2. Does a worker serve the job's lane? A job of a lane no worker lists in
   `WORKER_LANES` never runs.
3. Does the job fail? Its error is in the worker logs (`job_name=...`,
   "failed") and in Sentry when it is configured; the run record is in
   `periodic_job_runs` with `last_error`.
4. Is a worker stuck in a long job? Periodic jobs of one worker run one
   after another in its periodic thread: a hung job delays the others
   ([stuck-worker](stuck-worker.md)).

## Mitigate and fix

- Restart the worker that serves the lane, or add the lane to a worker's
  `WORKER_LANES`.
- Fix the failing job and deploy; the next success clears the alert (it
  resolves on the next check).
- A job removed by a deploy is never reported: its heartbeat keeps the old
  release's stamp (a worker's success never restamps it; only a starting
  worker does), and a starting worker forgets it once it is a week overdue.
