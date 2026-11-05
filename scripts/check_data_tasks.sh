#!/usr/bin/env bash
# Deploy guard: may the next release be promoted to production?
#
#   scripts/check_data_tasks.sh https://workshop-api.onrender.com
#
# Reads `checks.data_tasks` of GET /readyz on the production API: the
# post-deploy data tasks of the release production runs now (document
# migrations and lookup backfills, docs/operations/deploys.md). The next
# release may stop reading the old shape of the data, so it is promoted only
# once every task is done:
#   - `open` is 0                       -> exit 0, promote;
#   - tasks are open (failed ones too)  -> exit 1, wait for the batch worker
#                                          or retry a failed task on the
#                                          system page;
#   - no `data_tasks` line at all       -> exit 0: production runs a release
#                                          from before data tasks existed;
#   - `skipped`, no answer, not JSON    -> exit 1: the guard cannot tell.
# Needs bash, curl and python3. Exit codes: 0 promote, 1 wait, 2 wrong usage.
set -euo pipefail

if [ "$#" -ne 1 ] || [ -z "$1" ]; then
  sed -n '2,18p' "$0" >&2
  exit 2
fi

api_url="${1%/}"
request_seconds="${GUARD_REQUEST_SECONDS:-15}"
body_file="$(mktemp)"
trap 'rm -f "$body_file"' EXIT

# /readyz answers 503 when the instance cannot take traffic; its body still
# says how far the data tasks are.
status="$(curl --silent --show-error --max-time "$request_seconds" \
  --output "$body_file" --write-out '%{http_code}' \
  --header 'X-Request-Id: data-task-guard' "$api_url/readyz" 2>/dev/null || true)"
if [ "$status" != "200" ] && [ "$status" != "503" ]; then
  echo "WAIT  GET $api_url/readyz answered ${status:-nothing}: the data tasks are unknown." >&2
  exit 1
fi

python3 - "$body_file" <<'PYTHON'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as body_file:
        report = json.load(body_file)
    checks = report["checks"]
except (OSError, ValueError, KeyError, TypeError):
    print("WAIT  /readyz did not answer a readiness report.", file=sys.stderr)
    sys.exit(1)

line = checks.get("data_tasks") if isinstance(checks, dict) else None
if line is None:
    print("ok    production reports no data tasks (a release from before them).")
    sys.exit(0)

if not isinstance(line, dict) or line.get("status") == "skipped":
    print("WAIT  production could not read its data tasks.", file=sys.stderr)
    sys.exit(1)

open_count = line.get("open")
failed = line.get("failed") or 0
stalled = line.get("stalled") or 0
if open_count == 0:
    print("ok    every post-deploy data task of production is done.")
    sys.exit(0)

print(
    f"WAIT  {open_count} post-deploy data task(s) of production are not done "
    f"({failed} failed, {stalled} stalled): the next release is promoted once "
    "they are (admin system page, docs/operations/deploys.md).",
    file=sys.stderr,
)
sys.exit(1)
PYTHON
