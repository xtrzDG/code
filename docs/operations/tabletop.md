# Yearly tabletop exercise

Once a year, in the second half of January (after the holiday freeze, before
the spring season), the whole team walks one incident through on paper:
who notices, who decides, what owners are told, which runbook is missing a
step. The scripted game days of `tests/chaos/` prove the machinery on every
pull request; the tabletop proves the people and the documents.
`tests/legal/test_operations_documents.py` fails when the last exercise is
more than a year old and none is planned.

## How it runs (two hours)

1. **Before**: the facilitator (not the incident lead of the day) picks a
   scenario below that was not used in the last two years and prepares
   three injects: what is seen first, what gets worse, a surprise.
2. **Walk-through**: the team plays it in real time order. At each inject:
   which alert or person notices, which severity (`docs/operations/on-call.md`),
   who is lead and who is scribe (the scribe keeps the exercise's timeline
   as in a real incident), which runbook, what the owners and the status page say,
   which clock runs (the 48 hours of DPA 12.1, the businesses' 72 hours).
3. **Findings**: every missing step, wrong contact or unclear decision is a
   finding with an owner and a date, tracked like a postmortem's action
   items (`docs/operations/maintenance.md`, "Postmortems").
4. **Record**: one row below, the findings linked.

## Scenarios

| Scenario | Exercises |
| --- | --- |
| A business's export link is sent to the wrong person, who downloads it | breach triage, `runbooks/data-breach.md`, the notice through `POST /v1/admin/incidents` |
| A platform admin's laptop is stolen with a signed-in session | `docs/operations/offboarding.md`, session revocation, secret rotation |
| `ENCRYPTION_KEY` is pasted into a public chat | `docs/security/secrets-inventory.md`, "Key rotation" of `docs/operations/backup-restore.md` |
| The model provider is down on a Saturday at 20:30 | `runbooks/llm-outage.md`, owner notices, the status page |
| Render's Frankfurt region is unavailable for hours | `runbooks/render-outage.md`, restore elsewhere from the off-site backup |
| SMS pumping through the login form at night | `runbooks/sms-pumping.md`, provider budgets |
| A prompt injection makes the assistant offer a free booking | `runbooks/assistant-quality.md`, pausing the assistant of a business |
| A forged payment webhook marks deposits as paid | `docs/operations/on-call.md` question 2, the PSP's dashboard, the PSP's notification clock (`docs/operations/incident.md`) |
| Calls are transferred to premium numbers abroad overnight | `runbooks/irsf-toll-fraud.md`, provider spend limits, the founder's call at night |

## Record

| Date | Scenario | Facilitator | Participants | Findings |
| --- | --- | --- | --- | --- |
| 2027-01-19 (planned) | A business's export link is sent to the wrong person | [name] | [names] | [to record] |
