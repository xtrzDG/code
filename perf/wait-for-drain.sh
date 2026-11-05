#!/usr/bin/env bash
# Wait until the load stack's worker has drained the customer lanes of the
# job queue (inbound answers, outbound sends): no job of those lanes due
# now and none running. The k6 scenarios run one after the other, and a
# scenario's backlog (the widget visitors' messages) would otherwise load
# the next one (docs/operations/capacity.md). Jobs queued for later (a
# failed send's next attempt) do not count: they load nothing now.
#
#   perf/wait-for-drain.sh "before the webhook burst" [timeout seconds]
#
# Bounded: after the timeout (600 s by default) the run goes on with a
# warning, as the backlog left is reported (the scenarios' thresholds
# decide, not this wait). Each wait is a line of the job summary.
set -euo pipefail

label="$1"
timeout_seconds="${2:-600}"
compose=(docker compose -f docker-compose.yml -f perf/docker-compose.perf.yml)
query="select count(*) from workshop.queued_jobs
  where doc_lane in ('inbound', 'outbound')
    and (doc_status = 'running'
      or (doc_status = 'pending'
        and doc_run_at <= (extract(epoch from clock_timestamp()) * 1000000)::bigint))"

summary() {
  if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    echo "- Queue $label: $1" >> "$GITHUB_STEP_SUMMARY"
  fi
}

started=$SECONDS
while true; do
  left=$("${compose[@]}" exec -T postgres psql --username postgres \
    --dbname "${WORKSHOP_DB_NAME:-workshop}" --tuples-only --no-align \
    --command "$query")
  waited=$((SECONDS - started))
  if [ "$left" = "0" ]; then
    echo "Queue drained $label after ${waited} s."
    summary "drained after ${waited} s"
    exit 0
  fi
  if [ "$waited" -ge "$timeout_seconds" ]; then
    echo "::warning::$left customer jobs still due or running $label after ${waited} s."
    summary "$left jobs still due or running after ${waited} s"
    exit 0
  fi
  echo "$left customer jobs due or running $label (${waited} s)."
  sleep 5
done
