# 0008. Offline replay evaluations on every change, live ones every night

- Status: Accepted
- Date: 2026-10-22

## Context

What the assistant says is the product. A prompt edit, a new tool, a change
of the conversation engine or the reply guard can make it quote a wrong
price, skip a booking, answer in the wrong language or leak another
customer's data, and unit tests do not see it: they check code paths, not
conversations. Live model calls on every pull request are slow, cost money,
need keys CI forks do not have, and are not deterministic, so a red run
says little. Without a measurement on every change, regressions reach
customers and are found by owners.

## Decision

- **A dataset per niche.** `evals/datasets/<niche>.yaml` holds a business
  and its scenarios (the core flows in ka, ru and en, he and ar for four
  niches, bookings seeded for the customer, memory, voice notes and photos,
  foreign and transliterated languages, attacks), each with the expectations
  scorers check: the reply language, the tools called, prices quoted, a
  handoff, nothing leaked. Every scenario plays a fresh business through the
  real engine in an in-memory `AppContainer` with a fixed clock; only the
  model is swapped.
- **Cassettes.** `RecordingLlmAdapter` writes every model answer to
  `evals/cassettes/<niche>.json`, keyed by a hash of the model, the
  instruction, the tool definitions and the conversation so far (with ids
  and nonces normalized); `ReplayLlmAdapter` answers only from that file and
  never reaches a provider.
- **Replay in every test run.** `tests/evals` replays every scenario offline
  in each `pytest` run and compares the result with
  `evals/baselines/scripted.json`. A request without a recording is a miss
  that marks the sample stale and says why (the instruction's diff, the
  tools added or removed, another model, another path), so a change that
  alters what the model would see fails with its reason and is re-recorded
  in the same pull request (`scripts.run_evals --record --update-baseline`).
  Coverage tests require a scenario for every assistant tool and every
  scenario kind.
- **Live every night.** `.github/workflows/evals-nightly.yml` plays the
  scenarios on real models, three samples each (pass^3), judged by a model
  of the other family, and fails a model whose pass^k or any criterion's
  pass rate fell by more than the tolerance against `evals/baselines/<model>.json`.

## Consequences

- Every pull request learns, without keys and in about a minute, whether it
  changed what the assistant sends and how; a stale cassette names the cause.
- Replay proves determinism and wiring, not the quality of a real model's
  answers: that comes from the nightly run, whose result arrives a day
  later and needs the provider keys as repository secrets.
- Cassettes are large files that change whenever the prompt or the tools
  do; parallel packages that touch either re-record, and the integrator
  re-records once more after merging them.
- The same scorers grade the autotests owners run before going live, so a
  scenario fixed in one place stays fixed in the other.
