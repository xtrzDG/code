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
  *)
    exec "$role" "$@"
    ;;
esac
