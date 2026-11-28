#!/usr/bin/env bash
# The failed tests' page snapshots and the API log's last lines, readable in
# the job's log itself (the report artifact has to be downloaded first).
# Run from web/ after a failed end-to-end or visual run (.github/workflows/ci.yml).
set -uo pipefail

find e2e/.artifacts/results -name error-context.md -print0 2>/dev/null |
  while IFS= read -r -d '' context; do
    echo "::group::${context}"
    head -c 20000 "${context}"
    echo "::endgroup::"
  done
# A visual run's differing screens: where each differs, a small region drawn
# in text (a test's page snapshot shows its last page, not the one that differed).
if find e2e/.artifacts/results -name '*-diff.png' -print -quit 2>/dev/null | grep -q .; then
  echo "::group::Where the screenshots differ"
  (cd .. && uv run --frozen python -m scripts.screenshot_diff_regions web/e2e/.artifacts/results) || true
  echo "::endgroup::"
fi
echo "::group::api.log, last 300 lines"
tail -n 300 e2e/.artifacts/api.log 2>/dev/null || true
echo "::endgroup::"
