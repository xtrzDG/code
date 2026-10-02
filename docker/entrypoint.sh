#!/bin/sh
# Entry point of the backend image: one image, three roles.
#
#   workshop api       HTTP API (uvicorn factory, proxy headers, $PORT)
#   workshop worker    background worker (periodic jobs and the job queue)
#   workshop migrate   apply the SQL migrations to $DATABASE_URL (one-shot);
#                      extra arguments go to the runner, e.g. --dry-run
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
    exec uvicorn app.main:create_application --factory \
      --host 0.0.0.0 --port "${PORT:-8000}" \
      --proxy-headers --no-server-header "$@"
    ;;
  worker)
    exec python -m app.worker_main "$@"
    ;;
  migrate)
    exec python -m app.gateways.cli.migrate "$@"
    ;;
  *)
    exec "$role" "$@"
    ;;
esac
