#!/bin/sh
# Entry point of the backend image: one image, three roles.
#
#   workshop api       HTTP API (uvicorn factory, proxy headers, $PORT)
#   workshop worker    background worker (periodic jobs and the job queue)
#   workshop migrate   apply the SQL migrations to $DATABASE_URL (one-shot);
#                      extra arguments go to the runner, e.g. --dry-run
#   workshop migrate-documents
#                      rewrite stored documents of older schema versions
#                      (one-shot, after a release is fully deployed), e.g.
#                      --collection bookings --batch 500 --dry-run
#   workshop backfill-lookup
#                      fill trigger-kept lookup columns of rows written before
#                      their migration (one-shot, after the deploy that added
#                      them), e.g. --collection contacts --field last_seen_at
#                      --batch 5000 --dry-run (migrations/README.md)
#   workshop backup    dump the database in one snapshot, encrypt it with age
#                      and upload it to the EU backup bucket, then apply the
#                      retention (Render cron, daily); --work-directory DIR
#   workshop restore-check
#                      restore the newest backup into a scratch database of
#                      RESTORE_CHECK_DATABASE_URL and check it (the weekly
#                      drill); --keep-database keeps it for a real restore
#                      (docs/operations/backup-restore.md)
#   workshop seed-load store a load-test dataset and write its manifest
#                      (never in production; docs/operations/capacity.md),
#                      e.g. --businesses 20 --messages 40000 --manifest m.json
#
# Anything else is executed as given, so `workshop workshop api` (a platform
# that keeps the ENTRYPOINT and passes the full command) also works.
set -eu

role="${1:-api}"
if [ "$#" -gt 0 ]; then
  shift
fi

case "$role" in
  api)
    # Client addresses come from X-Forwarded-For of the proxies listed in
    # FORWARDED_ALLOW_IPS (uvicorn reads it; default 127.0.0.1). List the
    # proxies' address ranges, never "*" (then the left-most, client-controlled
    # entry wins). Workers: WEB_CONCURRENCY (default 1).
    # On SIGTERM open requests get 25 s to finish (Render waits 30 s, see
    # maxShutdownDelaySeconds); idle keep-alive connections close after 5 s.
    exec uvicorn app.main:create_application --factory \
      --host 0.0.0.0 --port "${PORT:-8000}" \
      --proxy-headers --no-server-header \
      --timeout-graceful-shutdown 25 --timeout-keep-alive 5 "$@"
    ;;
  worker)
    exec python -m app.worker_main "$@"
    ;;
  migrate)
    exec python -m app.gateways.cli.migrate "$@"
    ;;
  migrate-documents)
    exec python -m app.gateways.cli.migrate_documents "$@"
    ;;
  backfill-lookup)
    exec python -m app.gateways.cli.backfill_lookup "$@"
    ;;
  seed-load)
    exec python -m app.gateways.cli.seed_load "$@"
    ;;
  backup)
    exec python -m app.gateways.cli.backup "$@"
    ;;
  restore-check)
    exec python -m app.gateways.cli.restore_check "$@"
    ;;
  *)
    exec "$role" "$@"
    ;;
esac
