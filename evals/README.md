# Evaluation harness

How well the assistant answers customers, measured the same way on every
pull request (offline, from recorded model answers) and every night
(live, against real models).

| Check | What it guards | Runs |
| --- | --- | --- |
| `tests/evals/test_replay_cassettes.py` | every scenario of every niche replays from `evals/cassettes` with no stale recording and the result matches `evals/baselines/scripted.json` | every CI run (`uv run pytest`), no network, no keys |
| `scripts/run_evals.py --record --model <model>` | real models play the scenarios: pass^k, per-criterion rates, judge scores, cost and latency, compared with `evals/baselines/<model>.json` | nightly and on demand (`.github/workflows/evals-nightly.yml`) |

## What is played

`evals/datasets/<niche>.yaml` holds one business and its scenarios: 16
niches, eight scenarios in each of ka, ru and en, plus he and ar for
restaurant, hotel, beauty_salon and clinic (448 scenarios). Each scenario
is played against a fresh business through the real conversation engine
(`ConversationTurnOrchestrator`), in an in-memory `AppContainer` with a
fixed clock (Monday 5 October 2026, 12:00 in Tbilisi). Only the model is
swapped.

```yaml
niche: hotel
business:                         # seed: starter (default) or demo_tbilisi_restaurant
  name: Rustaveli Terrace Hotel
  languages: [ka, ru, en, he, ar]
  prices: {standard_room: '180'}  # starter offer key -> amount in major units
  answers: {breakfast: '...'}     # frequent questions only the owner can answer
scenarios:
- id: stay__en                    # unique per dataset; the report key is niche/id
  language: en                    # the reply language every answer must use
  kind: booking                   # an AutotestScenarioKind
  persona: {name: Emma, phone: '+447911123456'}
  goal: Book a standard double room for 2 nights from Thursday...
  item: Standard double room      # optional: the offer a price question is about
  customer: ['Hello! I would like to book...', 'Yes, please book it.']
  assistant:                      # the reference conversation (scripted model)
  - call: {check_availability: {date: '2026-10-08', nights: 2, party_size: 2}}
  - {say: 'Thursday for 2 nights is free...'}
  - call: {create_booking: {name: Emma, phone: '+447911123456', ...}}
  - {say_result: customer_message} # the text a tool result carries
  expect:
    tools:                        # tool names, or a name with required input fields
    - check_availability
    - create_booking: {name: [Emma], phone: '+447911123456', nights: 2}
    forbidden_tools: [create_lead]
    prices: ['180']               # amounts that must appear in the replies
    facts: ['14:00', [breakfast, завтрак]]  # each: a text or acceptable spellings
    forbidden: ['15%']            # values no reply may contain
    handoff: false                # whether a person must be called in
```

`customer` and `assistant` are the reference conversation the scripted model
plays, so the harness runs offline and the seeded cassettes start from a
known-good conversation. A live assistant improvises; its AI customer is
prompted with `build_customer_persona_prompt` from `goal` and `persona`
(the goal comes from `plan_scenarios` when a scenario leaves it out), and
it is scored by the same `expect`.

## Scoring

Deterministic scorers (`app/utilities/assembly/eval_scorers.py`,
`eval_text_scorers.py`, `eval_field_matching.py`) check every sample:

| Criterion | Passes when |
| --- | --- |
| `language` | every reply is written in the scenario language's script |
| `disclosure` | the AI disclosure opens the first reply, in the reply language's script, and appears nowhere else |
| `tool_calls` | every expected tool was called and no forbidden one was |
| `booking_fields` | the booking's name, phone, date, time, party size and nights match the persona (phones compared by digits) |
| `prices` | each expected price is in the replies, read the way the reply guard reads numbers |
| `required_facts` | each fact (or one of its spellings) is in the replies |
| `forbidden_values` | no reply contains a forbidden value |
| `handoff` | a person was called in exactly when expected |
| `guard` | the invented-numbers guard let every reply through unchanged (no rewrite, no handoff) |
| `records` | the autotest checks of what was created (bookings, leads, handoffs) pass |

A sample passes when every criterion it checks passes. A scenario passes
(pass^k) when all its `--samples` samples pass; pass@1 counts samples. With
`--judge-model` the judge prompt of the autotests also scores each sample
from 1 to 5; judge scores are reported, not gated.

## Cassettes and replay

`RecordingLlmAdapter` (`app/adapters/llm/recording_llm_adapter.py`) wraps a
real adapter and writes every answer to `evals/cassettes/<niche>.json`;
`ReplayLlmAdapter` answers from that file and never reaches a provider. An
answer is keyed by the hash of the model, the instruction, the tool
definitions and the conversation so far (ids, call ids and fence nonces are
replaced by numbered placeholders, so two runs of the same conversation
share a key). Instructions and tool sets are stored once and referenced by
digest; each key holds one take per sample.

A request with no recording is a miss: the engine sees the provider as down,
the sample is marked stale, and the report says why, comparing with the
closest recording:

- `The instruction changed since the recording:` and a unified diff of the
  prompt;
- `The offered tools changed since the recording:` with the tools added or
  removed (or that only their descriptions or schemas changed);
- the model id changed;
- otherwise the conversation took another path, with the last recorded
  message for comparison.

So a prompt, tool or engine change that alters what the model would see
makes `tests/evals` fail with the reason, and the cassettes are re-recorded
in the same pull request:

```bash
uv run python -m scripts.run_evals --record --update-baseline --workers 4
```

`--record` with the default model `scripted` plays the reference
conversations offline and deterministically (about half a minute for all
niches); commit `evals/cassettes` and `evals/baselines/scripted.json`
together. A reference conversation that no longer passes (for example a
tool now refuses an input) shows up in the report and in
`git diff evals/baselines`.

## Running

```bash
uv run python -m scripts.run_evals                         # replay every cassette
uv run python -m scripts.run_evals --niche hotel --language he
uv run python -m scripts.run_evals --record --model gpt-5-mini \
    --judge-model claude-opus-5-5 --samples 3 --workers 8 \
    --cassettes reports/evals/cassettes                    # live benchmark
```

| Option | Meaning |
| --- | --- |
| `--record` | play with `--model` and write cassettes (default: replay) |
| `--niche`, `--language`, `--scenario` | repeatable filters |
| `--model` | assistant model (`scripted`, or any id the platform routes: `gpt-5-mini`, `claude-opus-5-5`, ...) |
| `--customer-model` | AI customer model (default: the judge, else the assistant model) |
| `--judge-model` | judge model (default: no judge) |
| `--samples` | the k of pass^k (default 1; the nightly run uses 3) |
| `--turn-limit` | customer messages per conversation (default 6) |
| `--workers` | niches played at once, in separate processes |
| `--datasets`, `--cassettes`, `--baselines`, `--out` | directories (defaults under `evals/`, report in `reports/evals`) |
| `--tolerance` | allowed pass-rate drop against the baseline (default 0.05) |
| `--update-baseline` | store this run as `evals/baselines/<model>.json` |
| `--require-pass` | fail when any scenario fails |

Exit code 1: the pass rate fell by more than the tolerance against the
baseline (only scenarios both runs played are compared), a replayed cassette
is stale, or `--require-pass` saw a failure. Exit code 2: a dataset is
invalid.

The run writes `report.json` and `report.html` to `--out`: pass^k and
pass@1, per-criterion rates, judge averages, list-price cost of the tokens
used (`DEFAULT_LLM_TOKEN_PRICES`), p50 and p95 of the assistant's model time
per turn, a niche by language matrix, the change against the baseline with
the scenarios that started or stopped passing, and every scenario with its
transcript, tool calls and failed checks (failing ones first).

## Live benchmark

`.github/workflows/evals-nightly.yml` runs nightly and on demand (niches,
samples, tolerance and whether to store the baseline are inputs). It plays
`gpt-5-mini` judged by `claude-opus-5-5` and the reverse, three samples per
scenario, and fails a model whose pass rate fell beyond the tolerance. The
report, the recorded cassettes and (when asked) the new baseline are kept as
an artifact for 30 days; a baseline is accepted by committing it in a pull
request.

Repository secrets: `OPENAI_API_KEY` (and `OPENAI_PROJECT_ID` when the key
is a project key) and `ANTHROPIC_API_KEY`. Without both keys the job is
skipped with a notice. Locally the same variables are read from the
environment; nothing else is: the harness uses its own in-memory settings
and never touches a database or a channel.
