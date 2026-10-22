# Code health ratchets

Several packages are built in parallel every wave, and copy-paste, unused
code and untyped wiring grow quietly unless something stops them. Each
measure below is a ratchet: CI fails when it gets worse, and the recorded
number comes down when someone makes it better. Never raise a recorded
number to make a change pass; fix the change, or record the reason in its
pull request when a reviewer agrees that the number must move.

| Measure | Where it is recorded | What fails |
| --- | --- | --- |
| Duplicated share of `app/`, `scripts/`, `web/src/` | `"threshold"` in [`.jscpd.json`](../../.jscpd.json) | jscpd, when the share rises above it |
| Clones of more than 20 lines | [`.jscpd-large-clones.json`](../../.jscpd-large-clones.json) | `scripts/check_duplication.py`, on a clone the list lacks or a listed one that is gone |
| Names in `vulture_whitelist.py` | `WHITELISTED_NAMES` in `tests/architecture_policy/test_dead_code.py` | pytest, when the number differs |
| Unused cabinet exports, files and dependencies | none allowed (`web/knip.config.ts`) | `npm run knip` |
| `# type: ignore` comments in `app/containers` | `CONTAINER_TYPE_IGNORES` in `tests/architecture_policy/test_container_ignores_ratchet.py` | pytest, when the number differs or an ignore is not of the edge kind |
| Lines per hand-written file | 300 (`tests/architecture_policy/test_source_file_size.py`, ESLint `max-lines`) | pytest and ESLint |

## Duplication (jscpd)

[jscpd](https://github.com/kucherenko/jscpd) finds clones of at least 8
lines in the Python, JavaScript and TypeScript of `app/`, `scripts/` and
`web/src/`. The composition root (`app/containers/`, wiring that repeats by
design), the generated API client and tables and the translation
dictionaries are left out. CI downloads jscpd's prebuilt Linux binary pinned
by version and checksum (`JSCPD_VERSION`, `JSCPD_SHA256` in
`.github/workflows/ci.yml`); locally:

```bash
just duplication          # jscpd (npx jscpd@5.4.0) and the large-clone check
```

jscpd itself fails when the duplicated share of lines rises above
`"threshold"`. The check then compares the clones of more than 20 lines with
`.jscpd-large-clones.json`, which lists them by the pair of files they join:

- a clone between a pair the list does not have, or one clone more for a
  listed pair, fails with both places named. Extract the shared code into
  one helper (a function, a collaborator injected into both use cases, or a
  shared module of the role, such as `app/use_cases/shared/`) instead of
  listing the clone;
- a listed clone that is gone fails too, so the list shrinks with the code:
  `uv run python -m scripts.check_duplication --update` rewrites it;
- when the share falls well below the threshold, the check prints the lower
  threshold to record.

Examples of such helpers: `MemberMutationGuard` (`app/use_cases/businesses/`)
for every change to a team member, `check_limit_policy.py`
(`app/use_cases/users/`) for login codes and second factors alike,
`BookingStatusTransition` (`app/use_cases/bookings/`) for a staff change of a
booking and its Undo.

## Dead code (vulture and knip)

vulture runs in pytest (`tests/architecture_policy/test_dead_code.py`) over
`app/` and `scripts/`. Delete code nothing uses; only a name used from
outside Python (a serialized field, an enum value on the wire, a test or
operator seam) goes into `vulture_whitelist.py`, one name per line in the
section that explains why. The test holds the whitelist at
`WHITELISTED_NAMES` names: a new entry replaces one that is gone, and the
number comes down when an entry leaves. knip does the same for the cabinet
with no allowance at all (`npm run knip` in the `web-checks` job).

## Untyped wiring (container ignores)

dependency-injector types a child container's edge as the provider it is, so
each edge in `app/containers/` carries `# type: ignore[assignment]`
(`app/containers/AGENTS.md`). `test_container_ignores_ratchet.py` keeps
their number from growing and allows no other kind of ignore there. A new
context is wired as a typed root in plain Python instead, like the pilot
`app/containers/feedback/` ([ADR 0010](../adr/0010-composition-root.md));
when a context moves out of the provider graph, the recorded number comes
down.
