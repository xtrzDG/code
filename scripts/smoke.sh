#!/usr/bin/env bash
# Smoke test of a deployed Assistant Workshop: is the release up and usable?
#
#   scripts/smoke.sh https://workshop-api.onrender.com [https://workshop-cabinet.onrender.com]
#
# Checks, in order (the first failure stops it with exit code 1):
#   1. GET  /healthz                    answers {"status": "ok"} (retried while
#                                       the instance starts, SMOKE_WAIT_SECONDS),
#      GET  /readyz                     then {"status": "ready"} (database,
#                                       migrations and pool are fine)
#   2. GET  /widget.js                  serves the website widget
#   3. GET  /v1/auth/login-options      sign-in works and names its channels
#   4. nothing a release must not publish answers 2xx: /.git/HEAD,
#      /.git/config, /docs, /redoc, /openapi.json of the API
#      (SMOKE_ALLOW_API_DOCS=1 skips the three docs paths: APP_ENV=development
#      serves them), and of the cabinet /.git/HEAD and the source map of
#      the first script its /login page loads
#   5. GET  <cabinet>/login             the cabinet answers (if its URL is given)
#      GET  <cabinet>/.well-known/security.txt  names the security mailbox
#                                       and its https Canonical address
#   6. a test chat through the website widget of SMOKE_WIDGET_BUSINESS_ID
#      (only when set): config, one visitor message, an assistant answer
#      (in the response, or polled from GET .../messages); with
#      SMOKE_EXPECT_REPLY the answer must contain that text.
#
# Staging rehearses production with a real model (render.staging.yaml), so
# its test chat is one model answer per deploy; leave SMOKE_EXPECT_REPLY
# empty there (any answer passes). Leave SMOKE_WIDGET_BUSINESS_ID unset for
# production unless that answer is wanted too. Needs bash, curl, python3.
# Exit codes: 0 all passed, 1 a check failed, 2 wrong usage.
set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  sed -n '2,30p' "$0" >&2
  exit 2
fi

api_url="${1%/}"
cabinet_url="${2:-}"
cabinet_url="${cabinet_url%/}"
wait_seconds="${SMOKE_WAIT_SECONDS:-60}"
request_seconds="${SMOKE_REQUEST_SECONDS:-15}"
reply_seconds="${SMOKE_REPLY_SECONDS:-30}"
business_id="${SMOKE_WIDGET_BUSINESS_ID:-}"
expected_reply="${SMOKE_EXPECT_REPLY:-}"
body_file="$(mktemp)"
trap 'rm -f "$body_file"' EXIT

pass() { printf 'ok    %s\n' "$1"; }
fail() {
  printf 'FAIL  %s\n' "$1" >&2
  if [ -s "$body_file" ]; then
    printf '      response: %s\n' "$(head -c 500 "$body_file")" >&2
  fi
  exit 1
}

# refuse_published BASE PATH: fail when BASE PATH answers 2xx, which it
# must not (the body is not printed: it may hold what must stay hidden).
refuse_published() {
  local status
  status="$(request GET "$1$2")"
  case "$status" in
    2??)
      : >"$body_file"
      fail "GET $1$2 answered $status: a release must not publish it"
      ;;
  esac
}

# request METHOD URL [JSON_BODY] [HEADER]: the status code; the body goes to
# $body_file. A connection failure is status 000.
request() {
  local method="$1" url="$2" data="${3:-}" header="${4:-X-Smoke-Test: 1}"
  local arguments=(--silent --show-error --max-time "$request_seconds"
    --output "$body_file" --write-out '%{http_code}' --request "$method"
    --header "$header" --header "X-Request-Id: smoke-$$")
  if [ -n "$data" ]; then
    arguments+=(--header 'Content-Type: application/json' --data "$data")
  fi
  curl "${arguments[@]}" "$url" 2>/dev/null || true
}

# json_field NAME: a top-level field of the JSON body as text (objects and
# lists as JSON), or `assistant_reply`: the text of the first assistant
# message in `items`. Prints nothing when it is missing, null or empty.
json_field() {
  python3 - "$1" "$body_file" <<'PYTHON' 2>/dev/null || true
import json
import sys

name, path = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as body_file:
    body = json.load(body_file)
if not isinstance(body, dict):
    sys.exit(0)
if name == "assistant_reply":
    value = next(
        (
            item.get("text")
            for item in body.get("items", [])
            if isinstance(item, dict) and item.get("author") == "assistant"
        ),
        None,
    )
else:
    value = body.get(name)
if value not in (None, "", [], {}):
    print(value if isinstance(value, str) else json.dumps(value))
PYTHON
}

# 1. The instance is up (Render may still be switching traffic).
deadline=$((SECONDS + wait_seconds))
until [ "$(request GET "$api_url/healthz")" = "200" ] \
  && [ "$(json_field status)" = "ok" ]; do
  if [ "$SECONDS" -ge "$deadline" ]; then
    fail "GET /healthz did not answer {\"status\": \"ok\"} within ${wait_seconds}s"
  fi
  sleep 2
done
pass "GET /healthz"

status="$(request GET "$api_url/readyz")"
[ "$status" = "200" ] && [ "$(json_field status)" = "ready" ] \
  || fail "GET /readyz answered $status (database, migrations or pool)"
pass "GET /readyz"

# 2. The widget script every business site loads.
status="$(request GET "$api_url/widget.js")"
[ "$status" = "200" ] || fail "GET /widget.js answered $status"
grep -q 'function' "$body_file" || fail "GET /widget.js is not a script"
pass "GET /widget.js"

# 3. Sign-in options (the cabinet's first call).
status="$(request GET "$api_url/v1/auth/login-options")"
[ "$status" = "200" ] || fail "GET /v1/auth/login-options answered $status"
[ -n "$(json_field configured_channels)" ] \
  || fail "GET /v1/auth/login-options has no configured_channels"
pass "GET /v1/auth/login-options"

# 4. What a release must not publish (SEC-06).
hidden_paths=(/.git/HEAD /.git/config)
if [ "${SMOKE_ALLOW_API_DOCS:-}" != "1" ]; then
  hidden_paths+=(/docs /redoc /openapi.json)
fi
for path in "${hidden_paths[@]}"; do
  refuse_published "$api_url" "$path"
done
pass "API hides ${hidden_paths[*]}"

# 5. The cabinet.
if [ -n "$cabinet_url" ]; then
  status="$(request GET "$cabinet_url/login")"
  [ "$status" = "200" ] || fail "GET $cabinet_url/login answered $status"
  pass "GET cabinet /login"

  # Source maps go to the error tracker only (deleted after the upload).
  script_url="$(grep -Eo '(https?://[^"'"'"' ]+)?/_next/static/[^"'"'"' ?#]+\.js' \
    "$body_file" | head -n 1 || true)"
  [ -n "$script_url" ] || fail "cabinet /login loads no /_next/static script"
  if [[ "$script_url" == /* ]]; then
    script_url="$(printf '%s' "$cabinet_url" | sed -E 's#^(https?://[^/]+).*#\1#')$script_url"
  fi
  refuse_published "$cabinet_url" /.git/HEAD
  refuse_published "$script_url" .map
  pass "cabinet hides /.git/HEAD and its source maps"

  # RFC 9116: reports reach the platform's mailbox (SECURITY_CONTACT_EMAIL)
  # and the file names its own address (SITE_URL), SECURITY.md.
  status="$(request GET "$cabinet_url/.well-known/security.txt")"
  [ "$status" = "200" ] \
    || fail "GET $cabinet_url/.well-known/security.txt answered $status"
  grep -Eq '^Contact: mailto:[^[:space:]@]+@[^[:space:]@]+$' "$body_file" \
    || fail "security.txt names no security mailbox (SECURITY_CONTACT_EMAIL)"
  grep -Eq '^Canonical: https://[^[:space:]]+/\.well-known/security\.txt$' "$body_file" \
    || fail "security.txt has no https Canonical address (SITE_URL)"
  pass "GET cabinet /.well-known/security.txt"
fi

# 6. A test chat through the website widget.
if [ -z "$business_id" ]; then
  printf 'skip  test chat (SMOKE_WIDGET_BUSINESS_ID is not set)\n'
  exit 0
fi

widget_url="$api_url/v1/widget/$business_id"
session_key="smoke_$(date +%s)_$$_${RANDOM}"
status="$(request GET "$widget_url/config")"
[ "$status" = "200" ] || fail "GET widget config answered $status"
pass "GET widget config"

status="$(request POST "$widget_url/messages" \
  "{\"session_key\": \"$session_key\", \"text\": \"Hello! Are you open today?\"}")"
case "$status" in
  200 | 202) ;;
  *) fail "POST widget message answered $status" ;;
esac
reply="$(json_field text)"
cursor="$(json_field cursor)"

deadline=$((SECONDS + reply_seconds))
while [ -z "$reply" ]; do
  if [ "$SECONDS" -ge "$deadline" ]; then
    fail "no assistant answer in the widget within ${reply_seconds}s"
  fi
  sleep 2
  query=""
  [ -n "$cursor" ] && query="?after=$cursor"
  status="$(request GET "$widget_url/messages$query" "" \
    "X-Widget-Session-Key: $session_key")"
  [ "$status" = "200" ] || fail "GET widget messages answered $status"
  reply="$(json_field assistant_reply)"
done

if [ -n "$expected_reply" ] && [[ "$reply" != *"$expected_reply"* ]]; then
  fail "the assistant answered \"$reply\", without \"$expected_reply\""
fi
pass "test chat: \"$(printf '%s' "$reply" | tr '\n' ' ' | cut -c 1-80)\""
